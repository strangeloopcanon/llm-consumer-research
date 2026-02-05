import { useCallback, useEffect, useState, useRef } from 'react';
import {
  LayoutDashboard,
  Zap,
} from 'lucide-react';
import {
  listPersonaGroups,
  previewPanel,
  runSimulation,
  listRuns,
  getRunById,
  deleteRunById,
  buildAudience,
  type PanelPreviewResponse,
  type PersonaGroupSummary,
  type QuestionSpec,
  type PopulationSpecPayload,
  type SimulationRequest,
  type SimulationResponse,
  type RunSummary,
  type AudienceBuildResponse,
} from './api';
import type { RunRecord } from './types';
import { WizardView } from './components/WizardView';
import { DashboardView } from './components/DashboardView';

const RUN_STORAGE_KEY = 'ssr_run_history_v1';
const DRAFT_STORAGE_KEY = 'ssr_draft_config_v1';
const MAX_RUN_HISTORY = 20;

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null;

function App() {
  // Form State
  const [title, setTitle] = useState('RadiantSmile Whitening Toothpaste');
  const [description, setDescription] = useState(
    'A professional-grade whitening toothpaste that is safe for daily use. Features enamel-protection technology and a refreshing mint flavor.'
  );
  const [price, setPrice] = useState('$5.99');

  // Questions State
  const [questionnaire, setQuestionnaire] = useState<QuestionSpec[]>([
    {
      id: 'q1',
      intent: 'purchase_intent',
      text: 'How likely would you be to purchase this product?',
    },
  ]);

  // Population State
  const [populationMode, setPopulationMode] = useState<'library' | 'generate'>('library');
  const [personaGroup, setPersonaGroup] = useState('us_toothpaste_buyers');
  const [populationDescription, setPopulationDescription] = useState('');
  const [personaGroups, setPersonaGroups] = useState<PersonaGroupSummary[]>([]);
  const [personaGroupsLoading, setPersonaGroupsLoading] = useState(false);
  const [boostEnabled, setBoostEnabled] = useState(false);
  const [boostPrompt, setBoostPrompt] = useState('');
  const [boostShare, setBoostShare] = useState(0.3);
  const [boostCount, setBoostCount] = useState(2);
  const [boostStrategy, setBoostStrategy] = useState<'heuristic' | 'openai'>('openai');

  // Advanced State
  const [providers, setProviders] = useState<string[]>(['openai']);
  const [sampleSize, setSampleSize] = useState(50);
  const [temperature, setTemperature] = useState(0.7);
  const [additionalInstructions, setAdditionalInstructions] = useState('');
  const [panelSeed, setPanelSeed] = useState(0);
  const [panelContextText, setPanelContextText] = useState('');
  const [panelContextMode, setPanelContextMode] = useState<
    'shared' | 'round_robin' | 'sample'
  >('shared');
  const [panelContextChunksPerPersona, setPanelContextChunksPerPersona] = useState(3);

  // App State
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [panelPreview, setPanelPreview] = useState<PanelPreviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'population' | 'advanced'>('basic');
  const [includeRespondents, setIncludeRespondents] = useState(false);
  const [runHistory, setRunHistory] = useState<RunRecord[]>([]);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [baselineRunId, setBaselineRunId] = useState<string | null>(null);
  const showHistory = true;

  // Backend History State
  const [backendRuns, setBackendRuns] = useState<RunSummary[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Audience Builder State
  const [audienceFiles, setAudienceFiles] = useState<File[]>([]);
  const [audienceDescription, setAudienceDescription] = useState('');
  const [audienceBuilding, setAudienceBuilding] = useState(false);
  const [audienceResult, setAudienceResult] = useState<AudienceBuildResponse | null>(null);

  // Wizard Mode State
  const [viewMode, setViewMode] = useState<'dashboard' | 'wizard'>('wizard');
  const [wizardStep, setWizardStep] = useState(1);

  // UX State
  const fileInputRef = useRef<HTMLInputElement>(null);


  // Load draft config
  useEffect(() => {
    try {
      const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
      if (!raw) return;
      const draft = JSON.parse(raw);
      if (draft.title) setTitle(draft.title);
      if (draft.description) setDescription(draft.description);
      if (draft.price) setPrice(draft.price);
      if (draft.questionnaire) setQuestionnaire(draft.questionnaire);
      if (draft.populationMode) setPopulationMode(draft.populationMode);
      if (draft.personaGroup) setPersonaGroup(draft.personaGroup);
      if (draft.populationDescription) setPopulationDescription(draft.populationDescription);
    } catch {
      // Ignore
    }
  }, []);

  // Save draft config
  useEffect(() => {
    const draft = {
      title,
      description,
      price,
      questionnaire,
      populationMode,
      personaGroup,
      populationDescription,
    };
    localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  }, [title, description, price, questionnaire, populationMode, personaGroup, populationDescription]);

  useEffect(() => {
    let cancelled = false;
    setPersonaGroupsLoading(true);
    listPersonaGroups()
      .then((groups) => {
        if (cancelled) return;
        setPersonaGroups(groups);
        setPersonaGroup((current) =>
          groups.some((group) => group.name === current) ? current : (groups[0]?.name ?? current)
        );
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'Failed to load persona groups');
      })
      .finally(() => {
        if (cancelled) return;
        setPersonaGroupsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(RUN_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw) as RunRecord[];
      if (!Array.isArray(parsed) || parsed.length === 0) return;
      setRunHistory(parsed);
      const last = parsed[parsed.length - 1];
      if (last?.id && last?.response) {
        setCurrentRunId(last.id);
        setResult(last.response);
      }
    } catch {
      // Ignore malformed storage
    }
  }, []);

  useEffect(() => {
    try {
      const trimmed = runHistory.slice(-MAX_RUN_HISTORY);
      localStorage.setItem(RUN_STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // Ignore storage quota / permission errors
    }
  }, [runHistory]);

  const updateQuestion = (index: number, patch: Partial<QuestionSpec>) => {
    setQuestionnaire((prev) =>
      prev.map((q, idx) => (idx === index ? { ...q, ...patch } : q))
    );
  };

  const addQuestion = () => {
    setQuestionnaire((prev) => [
      ...prev,
      {
        id: `q${prev.length + 1}`,
        intent: prev[0]?.intent || 'purchase_intent',
        text: '',
      },
    ]);
  };

  const removeQuestion = (index: number) => {
    setQuestionnaire((prev) => prev.filter((_, idx) => idx !== index));
  };

  const handleImportQuestions = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      if (!text) return;

      const lines = text.split('\n');
      const newQuestions: typeof questionnaire = [];

      lines.forEach((line) => {
        const trimmed = line.trim();
        if (!trimmed) return;
        const parts = trimmed.split(',');
        const qText = parts[0].trim();
        const qIntent = parts[1]?.trim();

        if (qText) {
          newQuestions.push({
            id: `q${Date.now()}_${Math.random().toString(36).substr(2, 5)}`,
            text: qText,
            intent: qIntent || 'purchase_intent'
          });
        }
      });

      if (newQuestions.length > 0) {
        setQuestionnaire((prev) => [...prev, ...newQuestions]);
      }
      e.target.value = '';
    };
    reader.readAsText(file);
  };

  const buildRequestPayload = useCallback((): SimulationRequest => {
    const cleanedQuestionnaire = questionnaire
      .map((q, idx) => ({
        id: q.id || `q${idx + 1}`,
        text: (q.text || '').trim(),
        intent: q.intent || questionnaire[0]?.intent || 'purchase_intent',
      }))
      .filter((q) => q.text.length > 0);

    const trimmedBoostPrompt = boostPrompt.trim();
    const safeBoostShare = Number.isFinite(boostShare)
      ? Math.min(Math.max(boostShare, 0), 1)
      : 0.3;
    const safeBoostCount = Number.isFinite(boostCount) ? Math.max(boostCount, 1) : 2;
    const useBoost =
      populationMode === 'library' && boostEnabled && trimmedBoostPrompt.length > 0;
    const hasAudiencePopulation =
      populationMode === 'library' &&
      !useBoost &&
      Boolean(audienceResult?.population_spec);

    let populationSpec: PopulationSpecPayload | undefined;
    if (populationMode === 'generate') {
      populationSpec = {
        generations: [{ prompt: populationDescription, count: 4, strategy: 'openai' }],
      };
    } else if (useBoost) {
      populationSpec = {
        base_group: personaGroup,
        generations: [
          {
            prompt: trimmedBoostPrompt,
            count: safeBoostCount,
            strategy: boostStrategy,
            weight_share: safeBoostShare,
          },
        ],
      };
    } else if (hasAudiencePopulation) {
      populationSpec = audienceResult?.population_spec;
    }

    return {
      concept: { title, text: description, price },
      persona_group:
        populationMode === 'library' && !useBoost && !hasAudiencePopulation
          ? personaGroup
          : undefined,
      population_spec: populationSpec,
      questionnaire: cleanedQuestionnaire.length > 0 ? cleanedQuestionnaire : undefined,
      panel_context:
        panelContextText.trim().length > 0 && panelContextChunksPerPersona > 0
          ? {
            text: panelContextText,
            mode: panelContextMode,
            chunks_per_persona: panelContextChunksPerPersona,
          }
          : undefined,
      options: {
        n: sampleSize,
        providers,
        stratified: false,
        temperature,
        additional_instructions: additionalInstructions || undefined,
        seed: panelSeed > 0 ? panelSeed : undefined,
        include_respondents: includeRespondents || undefined,
      },
    };
  }, [
    additionalInstructions, boostCount, boostEnabled, boostPrompt, boostShare, boostStrategy,
    description, includeRespondents, panelContextChunksPerPersona, panelContextMode, panelContextText,
    panelSeed, personaGroup, populationDescription, populationMode, price, providers, questionnaire,
    sampleSize, temperature, title, audienceResult,
  ]);

  const handleSimulate = async () => {
    const payload = buildRequestPayload();
    const previousCurrent = currentRunId;
    setLoading(true);
    setError(null);
    setPanelPreview(null);
    try {
      const response = await runSimulation(payload);
      setResult(response);
      const runId = typeof response.metadata?.run_id === 'string'
        ? response.metadata.run_id
        : (typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`);

      const labelParts: string[] = [];
      if (title.trim()) labelParts.push(title.trim());
      if (payload.population_spec && !payload.persona_group) {
        labelParts.push('custom audience');
      } else {
        labelParts.push(populationMode === 'library' ? personaGroup : 'generated audience');
      }
      labelParts.push(`n=${sampleSize}`);
      if (panelSeed > 0) labelParts.push(`seed=${panelSeed}`);

      const record: RunRecord = {
        id: runId,
        label: labelParts.join(' · '),
        createdAt: Date.now(),
        request: payload,
        response,
      };
      setRunHistory((prev) => [...prev, record].slice(-MAX_RUN_HISTORY));
      setCurrentRunId(runId);
      setBaselineRunId((prev) => prev ?? previousCurrent);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const handlePreviewPanel = async () => {
    setPreviewing(true);
    setError(null);
    try {
      const response = await previewPanel(buildRequestPayload());
      setPanelPreview(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setPreviewing(false);
    }
  };

  const loadBackendHistory = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const runs = await listRuns(20);
      setBackendRuns(runs);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const handleLoadBackendRun = async (runId: string) => {
    try {
      const detail = await getRunById(runId);
      setResult(detail.response);
      setCurrentRunId(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load run');
    }
  };

  const handleDeleteBackendRun = async (runId: string) => {
    try {
      await deleteRunById(runId);
      setBackendRuns((prev) => prev.filter((r) => r.id !== runId));
      if (currentRunId === runId) {
        setResult(null);
        setCurrentRunId(null);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete run');
    }
  };

  useEffect(() => {
    loadBackendHistory();
  }, [loadBackendHistory]);

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) setAudienceFiles(Array.from(files));
  };

  const handleBuildAudience = async () => {
    if (audienceFiles.length === 0) {
      setError('Please select at least one file');
      return;
    }
    setAudienceBuilding(true);
    setError(null);
    try {
      const result = await buildAudience(audienceFiles, audienceDescription || undefined);
      setAudienceResult(result);
      setPopulationMode('library');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to build audience');
    } finally {
      setAudienceBuilding(false);
    }
  };

  const loadRun = (runId: string) => {
    const run = runHistory.find((item) => item.id === runId);
    if (!run) return;
    setCurrentRunId(runId);
    setResult(run.response);
    setPanelPreview(null);
  };

  const deleteRun = (runId: string) => {
    setRunHistory((prev) => {
      const next = prev.filter((item) => item.id !== runId);
      if (baselineRunId === runId) setBaselineRunId(null);
      if (currentRunId === runId) {
        const last = next[next.length - 1] ?? null;
        setCurrentRunId(last?.id ?? null);
        setResult(last?.response ?? null);
      }
      return next;
    });
  };

  const restoreConfigFromRun = (run: RunRecord) => {
    const req = run.request;
    setTitle(req.concept.title ?? '');
    setDescription(req.concept.text ?? '');
    setPrice(req.concept.price ?? '');

    if (req.questionnaire && req.questionnaire.length > 0) {
      setQuestionnaire(
        req.questionnaire.map((q, idx) => ({
          id: q.id || `q${idx + 1}`,
          intent: q.intent || 'purchase_intent',
          text: q.text || '',
        }))
      );
    }

    setProviders(req.options.providers ?? ['openai']);
    setSampleSize(typeof req.options.n === 'number' ? req.options.n : 50);
    setTemperature(typeof req.options.temperature === 'number' ? req.options.temperature : 0.7);
    setAdditionalInstructions(req.options.additional_instructions ?? '');
    setPanelSeed(req.options.seed ?? 0);
    setIncludeRespondents(Boolean(req.options.include_respondents));

    if (req.panel_context) {
      setPanelContextText(req.panel_context.text ?? '');
      setPanelContextMode(req.panel_context.mode ?? 'shared');
      setPanelContextChunksPerPersona(req.panel_context.chunks_per_persona ?? 3);
    } else {
      setPanelContextText('');
      setPanelContextMode('shared');
      setPanelContextChunksPerPersona(3);
    }

    const spec = req.population_spec;
    setAudienceResult(null);

    if (isRecord(spec) && 'base_group' in spec) {
      const baseGroup = typeof spec.base_group === 'string' ? spec.base_group : '';
      setPopulationMode('library');
      if (baseGroup) setPersonaGroup(baseGroup);

      const generation = Array.isArray(spec.generations) ? spec.generations[0] : undefined;
      const generationObj = isRecord(generation) ? generation : null;
      const prompt = generationObj && typeof generationObj.prompt === 'string' ? generationObj.prompt : '';
      const share =
        generationObj && typeof generationObj.weight_share === 'number'
          ? generationObj.weight_share
          : 0.3;
      const count = generationObj && typeof generationObj.count === 'number' ? generationObj.count : 2;
      const strategy =
        generationObj &&
          (generationObj.strategy === 'heuristic' || generationObj.strategy === 'openai')
          ? generationObj.strategy
          : 'openai';

      setBoostEnabled(Boolean(prompt));
      setBoostPrompt(prompt);
      setBoostShare(Math.min(Math.max(share, 0), 1));
      setBoostCount(Math.max(1, count));
      setBoostStrategy(strategy);
      setPopulationDescription('');
      return;
    }

    if (isRecord(spec) && Array.isArray(spec.generations) && !('base_group' in spec)) {
      const firstGeneration = isRecord(spec.generations[0]) ? spec.generations[0] : null;
      const prompt =
        firstGeneration && typeof firstGeneration.prompt === 'string'
          ? firstGeneration.prompt
          : '';
      setPopulationMode('generate');
      setPopulationDescription(prompt);
      setBoostEnabled(false);
      setBoostPrompt('');
      setBoostShare(0.3);
      setBoostCount(2);
      setBoostStrategy('openai');
      return;
    }

    if (isRecord(spec)) {
      setPopulationMode('library');
      setAudienceResult({
        population_spec: spec,
        reasoning: 'Loaded from run history.',
        evidence_summary_length: 0,
      });
      setBoostEnabled(false);
      setBoostPrompt('');
      setBoostShare(0.3);
      setBoostCount(2);
      setBoostStrategy('openai');
      setPopulationDescription('');
      return;
    }

    setPopulationMode('library');
    if (req.persona_group) setPersonaGroup(req.persona_group);
    setBoostEnabled(false);
    setBoostPrompt('');
    setBoostShare(0.3);
    setBoostCount(2);
    setBoostStrategy('openai');
    setPopulationDescription('');
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900 selection:bg-indigo-100 selection:text-indigo-900 pb-20">
      <header className="sticky top-0 z-30 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-indigo-200 shadow-lg">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <h1 className="font-bold text-xl tracking-tight text-slate-900">
              Consumer<span className="text-indigo-600">Sync</span>
            </h1>
          </div>

          <div className="flex bg-slate-100 p-1 rounded-lg">
            <button
              onClick={() => setViewMode('wizard')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${viewMode === 'wizard' ? 'bg-white shadow text-indigo-700' : 'text-slate-600 hover:text-slate-900'}`}
            >
              <Zap className="w-4 h-4" />
              Wizard
            </button>
            <button
              onClick={() => setViewMode('dashboard')}
              className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all flex items-center gap-2 ${viewMode === 'dashboard' ? 'bg-white shadow text-indigo-700' : 'text-slate-600 hover:text-slate-900'}`}
            >
              <LayoutDashboard className="w-4 h-4" />
              Dashboard
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {viewMode === 'wizard' ? (
          <WizardView
            setViewMode={setViewMode}
            wizardStep={wizardStep}
            setWizardStep={setWizardStep}
            title={title}
            setTitle={setTitle}
            description={description}
            setDescription={setDescription}
            price={price}
            setPrice={setPrice}
            populationMode={populationMode}
            setPopulationMode={setPopulationMode}
            personaGroup={personaGroup}
            setPersonaGroup={setPersonaGroup}
            populationDescription={populationDescription}
            setPopulationDescription={setPopulationDescription}
            sampleSize={sampleSize}
            setSampleSize={setSampleSize}
            personaGroups={personaGroups}
            questionnaire={questionnaire}
            updateQuestion={updateQuestion}
            addQuestion={addQuestion}
            removeQuestion={removeQuestion}
            handleImportQuestions={handleImportQuestions}
            loading={loading}
            handleSimulate={handleSimulate}
          />
        ) : (
          <DashboardView
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            title={title}
            setTitle={setTitle}
            description={description}
            setDescription={setDescription}
            price={price}
            setPrice={setPrice}
            sampleSize={sampleSize}
            setSampleSize={setSampleSize}
            questionnaire={questionnaire}
            updateQuestion={updateQuestion}
            addQuestion={addQuestion}
            removeQuestion={removeQuestion}
            handleImportQuestions={handleImportQuestions}
            populationMode={populationMode}
            setPopulationMode={setPopulationMode}
            personaGroup={personaGroup}
            setPersonaGroup={setPersonaGroup}
            personaGroups={personaGroups}
            personaGroupsLoading={personaGroupsLoading}
            audienceFiles={audienceFiles}
            setAudienceFiles={setAudienceFiles}
            audienceDescription={audienceDescription}
            setAudienceDescription={setAudienceDescription}
            audienceBuilding={audienceBuilding}
            audienceResult={audienceResult}
            handleBuildAudience={handleBuildAudience}
            handleFileSelect={handleFileSelect}
            fileInputRef={fileInputRef}
            boostEnabled={boostEnabled}
            setBoostEnabled={setBoostEnabled}
            boostPrompt={boostPrompt}
            setBoostPrompt={setBoostPrompt}
            boostShare={boostShare}
            setBoostShare={setBoostShare}
            boostCount={boostCount}
            setBoostCount={setBoostCount}
            boostStrategy={boostStrategy}
            setBoostStrategy={setBoostStrategy}
            populationDescription={populationDescription}
            setPopulationDescription={setPopulationDescription}
            providers={providers}
            setProviders={setProviders}
            temperature={temperature}
            setTemperature={setTemperature}
            additionalInstructions={additionalInstructions}
            setAdditionalInstructions={setAdditionalInstructions}
            panelSeed={panelSeed}
            setPanelSeed={setPanelSeed}
            panelContextText={panelContextText}
            setPanelContextText={setPanelContextText}
            panelContextMode={panelContextMode}
            setPanelContextMode={setPanelContextMode}
            panelContextChunksPerPersona={panelContextChunksPerPersona}
            setPanelContextChunksPerPersona={setPanelContextChunksPerPersona}
            includeRespondents={includeRespondents}
            setIncludeRespondents={setIncludeRespondents}
            handlePreviewPanel={handlePreviewPanel}
            handleSimulate={handleSimulate}
            loading={loading}
            previewing={previewing}
            error={error}
            panelPreview={panelPreview}
            activeResult={result}
            showHistory={showHistory}
            runHistory={runHistory}
            backendRuns={backendRuns}
            currentRunId={currentRunId}
            loadRun={loadRun}
            deleteRun={deleteRun}
            loadBackendHistory={loadBackendHistory}
            loadingHistory={loadingHistory}
            handleLoadBackendRun={handleLoadBackendRun}
            handleDeleteBackendRun={handleDeleteBackendRun}
            currentRun={runHistory.find((item) => item.id === currentRunId)}
            restoreConfigFromRun={restoreConfigFromRun}
            baselineRunId={baselineRunId}
            setBaselineRunId={setBaselineRunId}
            configMatchesCurrentRun={!currentRunId || JSON.stringify(buildRequestPayload()) === JSON.stringify(runHistory.find((r) => r.id === currentRunId)?.request)}
          />
        )}
      </main>
    </div>
  );
}

export default App;
