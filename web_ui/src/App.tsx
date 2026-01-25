import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import {
  LayoutDashboard,
  Play,
  Users,
  Settings,
  AlertCircle,
  Loader2,
  CheckCircle2,
  Download,
  Copy,
  History,
  Trash2,
  Upload,
  FileText,
  RefreshCw,
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
  type SimulationRequest,
  type SimulationResponse,
  type RunSummary,
  type AudienceBuildResponse,
} from './api';

type RunRecord = {
  id: string;
  label: string;
  createdAt: number;
  request: SimulationRequest;
  response: SimulationResponse;
};

type QuestionAggregate = NonNullable<SimulationResponse['questions']>[number];

const RUN_STORAGE_KEY = 'ssr_run_history_v1';
const DRAFT_STORAGE_KEY = 'ssr_draft_config_v1';
const MAX_RUN_HISTORY = 20;

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
  const [showHistory, setShowHistory] = useState(false);
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

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
  const resultsRef = useRef<HTMLDivElement>(null);
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

  // Auto-scroll to results
  useEffect(() => {
    if (result && resultsRef.current && !loading) {
      setTimeout(() => {
        resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }, [result, loading]);

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

  useEffect(() => {
    if (copyState === 'idle') return;
    const timer = window.setTimeout(() => setCopyState('idle'), 1500);
    return () => window.clearTimeout(timer);
  }, [copyState]);

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

        // Simple CSV parse: Text, Intent (optional)
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

      // Reset input
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

    return {
      concept: {
        title,
        text: description,
        price,
      },
      persona_group: populationMode === 'library' && !useBoost ? personaGroup : undefined,
      population_spec:
        populationMode === 'generate'
          ? {
            generations: [
              {
                prompt: populationDescription,
                count: 4,
                strategy: 'openai',
              },
            ],
          }
          : useBoost
            ? {
              base_group: personaGroup,
              generations: [
                {
                  prompt: trimmedBoostPrompt,
                  count: safeBoostCount,
                  strategy: boostStrategy,
                  weight_share: safeBoostShare,
                },
              ],
            }
            : undefined,
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
    additionalInstructions,
    boostCount,
    boostEnabled,
    boostPrompt,
    boostShare,
    boostStrategy,
    description,
    includeRespondents,
    panelContextChunksPerPersona,
    panelContextMode,
    panelContextText,
    panelSeed,
    personaGroup,
    populationDescription,
    populationMode,
    price,
    providers,
    questionnaire,
    sampleSize,
    temperature,
    title,
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

      const runId =
        typeof crypto !== 'undefined' && 'randomUUID' in crypto
          ? crypto.randomUUID()
          : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

      const labelParts: string[] = [];
      if (title.trim()) labelParts.push(title.trim());
      labelParts.push(populationMode === 'library' ? personaGroup : 'generated audience');
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

  // Backend History Handlers
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

  // Load backend history on mount/when history panel opens
  useEffect(() => {
    if (showHistory) {
      loadBackendHistory();
    }
  }, [showHistory, loadBackendHistory]);

  // Audience Builder Handlers
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files) {
      setAudienceFiles(Array.from(files));
    }
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
      // Switch to library mode - the generated spec is stored in audienceResult
      setPopulationMode('library');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to build audience');
    } finally {
      setAudienceBuilding(false);
    }
  };

  const toggleProvider = (p: string) => {
    setProviders((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const currentRun = useMemo(
    () => runHistory.find((item) => item.id === currentRunId) ?? null,
    [runHistory, currentRunId]
  );
  const baselineRun = useMemo(
    () => runHistory.find((item) => item.id === baselineRunId) ?? null,
    [runHistory, baselineRunId]
  );

  const draftRequestJson = useMemo(() => {
    try {
      return JSON.stringify(buildRequestPayload());
    } catch {
      return '';
    }
  }, [buildRequestPayload]);

  const currentRunRequestJson = useMemo(() => {
    if (!currentRun) return '';
    try {
      return JSON.stringify(currentRun.request);
    } catch {
      return '';
    }
  }, [currentRun]);

  const configMatchesCurrentRun = !currentRun || draftRequestJson === currentRunRequestJson;

  const formatTimestamp = (ts: number) =>
    new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });

  const downloadBlob = (contents: string, filename: string, mime: string) => {
    const blob = new Blob([contents], { type: mime });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const downloadJson = (data: unknown, filename: string) => {
    downloadBlob(JSON.stringify(data, null, 2), filename, 'application/json');
  };

  const flattenRespondentsToCsv = (response: SimulationResponse): string | null => {
    const rows: string[][] = [
      [
        'respondent_id',
        'persona_name',
        'persona_weight',
        'question_id',
        'intent',
        'anchor_bank',
        'provider',
        'model',
        'score_mean',
        'rationale',
      ],
    ];

    let hasRows = false;
    for (const personaResult of response.personas) {
      const personaName = personaResult.persona.name;
      const personaWeight = personaResult.persona.weight ?? 0;
      const respondents = personaResult.respondents || [];
      for (const respondent of respondents) {
        for (const answer of respondent.answers || []) {
          hasRows = true;
          rows.push([
            respondent.respondent_id,
            personaName,
            String(personaWeight),
            answer.question_id,
            answer.intent,
            answer.anchor_bank,
            answer.provider,
            answer.model,
            String(answer.score_mean),
            answer.rationale.replace(/\r?\n/g, ' ').trim(),
          ]);
        }
      }
    }

    if (!hasRows) return null;

    const escapeCsv = (value: string) => {
      const needsQuotes = /[",\n]/.test(value);
      const escaped = value.replace(/"/g, '""');
      return needsQuotes ? `"${escaped}"` : escaped;
    };

    return rows.map((row) => row.map(escapeCsv).join(',')).join('\n') + '\n';
  };

  const copyTextToClipboard = async (text: string): Promise<boolean> => {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch {
      // Fall back
    }

    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.left = '-9999px';
      textarea.style.top = '0';
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(textarea);
      return ok;
    } catch {
      return false;
    }
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

    const spec = req.population_spec as
      | {
        base_group?: unknown;
        generations?: Array<{
          prompt?: unknown;
          count?: unknown;
          strategy?: unknown;
          weight_share?: unknown;
        }>;
      }
      | undefined;

    if (spec && typeof spec === 'object' && 'base_group' in spec) {
      const baseGroup = typeof spec.base_group === 'string' ? spec.base_group : '';
      setPopulationMode('library');
      if (baseGroup) setPersonaGroup(baseGroup);

      const generation = Array.isArray(spec.generations) ? spec.generations[0] : undefined;
      const prompt = generation && typeof generation.prompt === 'string' ? generation.prompt : '';
      const share =
        generation && typeof generation.weight_share === 'number' ? generation.weight_share : 0.3;
      const count = generation && typeof generation.count === 'number' ? generation.count : 2;
      const strategy =
        generation && (generation.strategy === 'heuristic' || generation.strategy === 'openai')
          ? generation.strategy
          : 'openai';

      setBoostEnabled(Boolean(prompt));
      setBoostPrompt(prompt);
      setBoostShare(Math.min(Math.max(share, 0), 1));
      setBoostCount(Math.max(1, count));
      setBoostStrategy(strategy);
      setPopulationDescription('');
      return;
    }

    if (spec && typeof spec === 'object' && Array.isArray((spec as { generations?: unknown }).generations)) {
      const generations = (spec as { generations?: Array<{ prompt?: unknown }> }).generations ?? [];
      const prompt = typeof generations[0]?.prompt === 'string' ? generations[0]?.prompt : '';
      setPopulationMode('generate');
      setPopulationDescription(prompt);
      setBoostEnabled(false);
      setBoostPrompt('');
      setBoostShare(0.3);
      setBoostCount(2);
      setBoostStrategy('openai');
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
      if (baselineRunId === runId) {
        setBaselineRunId(null);
      }
      if (currentRunId === runId) {
        const last = next[next.length - 1] ?? null;
        setCurrentRunId(last?.id ?? null);
        setResult(last?.response ?? null);
      }
      return next;
    });
  };

  const activeResult = currentRun?.response ?? result;

  const respondentCsv = useMemo(() => {
    if (!activeResult) return null;
    return flattenRespondentsToCsv(activeResult);
  }, [activeResult]);

  const questionAggregatesFor = (response: SimulationResponse): QuestionAggregate[] => {
    if (response.questions && response.questions.length > 0) return response.questions;
    return [
      {
        question_id: 'q1',
        question: response.metadata?.question || 'Primary question',
        intent: response.metadata?.intent || 'purchase_intent',
        anchor_bank: response.metadata?.anchor_bank || '',
        aggregate: response.aggregate,
      },
    ];
  };

  const baselineAggregateMap = useMemo(() => {
    const base = baselineRun?.response;
    if (!base) return new Map<string, QuestionAggregate>();
    const entries = questionAggregatesFor(base).map((item) => [item.question_id, item] as const);
    return new Map(entries);
  }, [baselineRun]);

  const providersForActiveRun = currentRun?.request.options.providers ?? providers;

  const observedProviderModels = useMemo(() => {
    if (!activeResult) return null;
    const counts = new Map<string, number>();
    for (const personaResult of activeResult.personas) {
      for (const respondent of personaResult.respondents ?? []) {
        for (const answer of respondent.answers ?? []) {
          const key = `${answer.provider}:${answer.model}`;
          counts.set(key, (counts.get(key) ?? 0) + 1);
        }
      }
    }
    if (counts.size === 0) return null;
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([key, count]) => `${key} (${count})`)
      .join(', ');
  }, [activeResult]);

  const overallDeltas = useMemo(() => {
    const base = baselineRun?.response?.aggregate;
    if (!activeResult || !base) return null;
    return {
      meanDelta: activeResult.aggregate.mean - base.mean,
      top2Delta: activeResult.aggregate.top2box - base.top2box,
    };
  }, [activeResult, baselineRun]);

  const buildRunSummaryText = (response: SimulationResponse): string => {
    const conceptTitle = (currentRun?.request.concept.title ?? title).trim() || 'Untitled concept';
    const audience =
      currentRun?.request.persona_group ||
      response.metadata?.persona_group ||
      (populationMode === 'library' ? personaGroup : 'generated audience');

    const seed =
      typeof currentRun?.request.options.seed === 'number' && currentRun.request.options.seed > 0
        ? currentRun.request.options.seed
        : panelSeed > 0
          ? panelSeed
          : 0;

    const providersLabel = providersForActiveRun.join(', ');

    const lines: string[] = [];
    lines.push(`Synthetic consumer research — ${conceptTitle}`);
    const contextParts: string[] = [];
    if (audience) contextParts.push(`Audience: ${audience}`);
    contextParts.push(`n=${response.aggregate.sample_n}`);
    if (seed) contextParts.push(`seed=${seed}`);
    if (providersLabel) contextParts.push(`providers=${providersLabel}`);
    lines.push(contextParts.join(' · '));

    for (const item of questionAggregatesFor(response).slice(0, 3)) {
      const base = baselineAggregateMap.get(item.question_id);
      const deltaMean = base ? item.aggregate.mean - base.aggregate.mean : null;
      const deltaTop2 = base ? item.aggregate.top2box - base.aggregate.top2box : null;
      const delta =
        deltaMean !== null && deltaTop2 !== null
          ? ` (Δ mean ${deltaMean >= 0 ? '+' : ''}${deltaMean.toFixed(2)}, Δ top2 ${deltaTop2 >= 0 ? '+' : ''}${(deltaTop2 * 100).toFixed(0)}%)`
          : '';
      lines.push(
        `${item.question_id} (${item.intent}): mean=${item.aggregate.mean.toFixed(2)}, top2=${(item.aggregate.top2box * 100).toFixed(0)}%${delta}`
      );
    }

    return lines.join('\n');
  };

  const handleCopySummary = async () => {
    if (!activeResult) return;
    const ok = await copyTextToClipboard(buildRunSummaryText(activeResult));
    setCopyState(ok ? 'copied' : 'failed');
  };

  const chartData = activeResult?.aggregate.pmf.map((val, idx) => ({
    rating: idx + 1,
    percentage: (val * 100).toFixed(1),
  }));

  const hasValidQuestion = questionnaire.some((q) => (q.text || '').trim().length > 0);
  const primaryIntent =
    activeResult?.questions?.[0]?.intent || questionnaire[0]?.intent || 'purchase_intent';
  const intentLabel =
    ({
      purchase_intent: 'Purchase Intent',
      relevance: 'Relevance',
      trust: 'Trust',
      clarity: 'Clarity',
      value_for_money: 'Value for Money',
      differentiation: 'Differentiation',
    } as Record<string, string>)[primaryIntent] || primaryIntent;

  const selectedGroup = personaGroups.find((group) => group.name === personaGroup);
  const personaGroupLabel = (group: PersonaGroupSummary) =>
    `${group.name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())} (${group.persona_count})`;

  const toneForDelta = (delta: number | null | undefined) => {
    if (delta === null || delta === undefined) return 'bg-white border-slate-200';
    if (delta > 0) return 'bg-green-50/60 border-green-200';
    if (delta < 0) return 'bg-red-50/60 border-red-200';
    return 'bg-white border-slate-200';
  };

  const textForDelta = (delta: number) => {
    if (delta > 0) return 'text-green-700';
    if (delta < 0) return 'text-red-700';
    return 'text-white border-slate-200';
  };

  const renderWizard = () => {
    return (
      <div className="max-w-3xl mx-auto py-8">
        {/* Stepper */}
        <div className="mb-8">
          <div className="flex items-center justify-between relative">
            <div className={`absolute left-0 top-1/2 -translate-y-1/2 w-full h-1 bg-slate-200 -z-10`} />
            <div className={`absolute left-0 top-1/2 -translate-y-1/2 h-1 bg-indigo-600 -z-10 transition-all duration-500`} style={{ width: `${((wizardStep - 1) / 3) * 100}%` }} />

            {['Product', 'Audience', 'Survey', 'Review'].map((label, idx) => {
              const step = idx + 1;
              const isActive = wizardStep >= step;
              const isCurrent = wizardStep === step;
              return (
                <div key={label} className="flex flex-col items-center gap-2 bg-slate-50 px-2">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-colors ${isActive ? 'bg-indigo-600 border-indigo-600 text-white' : 'bg-white border-slate-300 text-slate-500'}`}>
                    {step}
                  </div>
                  <span className={`text-xs font-medium ${isCurrent ? 'text-indigo-700' : 'text-slate-500'}`}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
          <div className="p-8">
            {wizardStep === 1 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <h2 className="text-2xl font-bold text-slate-900">What are we testing?</h2>
                  <p className="text-slate-500">Define the product concept you want feedback on.</p>
                </div>

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Product Name</label>
                    <input type="text" value={title} onChange={e => setTitle(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="e.g. RadiantSmile Toothpaste" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                    <textarea value={description} onChange={e => setDescription(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none h-32 resize-none" placeholder="Describe the features, benefits, and value proposition..." />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1">Price</label>
                    <input type="text" value={price} onChange={e => setPrice(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:ring-2 focus:ring-indigo-500 outline-none" placeholder="e.g. $5.99" />
                  </div>
                </div>
              </div>
            )}

            {wizardStep === 2 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <h2 className="text-2xl font-bold text-slate-900">Who is the audience?</h2>
                  <p className="text-slate-500">Define the target demographics or select a saved group.</p>
                </div>

                <div className="flex justify-center mb-6">
                  <div className="bg-slate-100 p-1 rounded-lg flex">
                    <button onClick={() => setPopulationMode('generate')} className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${populationMode === 'generate' ? 'bg-white shadow text-indigo-700' : 'text-slate-600'}`}>Generate AI Panel</button>
                    <button onClick={() => setPopulationMode('library')} className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${populationMode === 'library' ? 'bg-white shadow text-indigo-700' : 'text-slate-600'}`}>Load Saved Group</button>
                  </div>
                </div>

                {populationMode === 'generate' ? (
                  <div className="space-y-4">
                    <textarea value={populationDescription} onChange={e => setPopulationDescription(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-slate-200 h-32" placeholder="Describe your target audience (e.g. US moms aged 25-40 who buy organic)..." />
                    <div className="flex items-center gap-4">
                      <label className="text-sm font-medium text-slate-700">Sample Size: <span className="text-indigo-600">{sampleSize}</span></label>
                      <input type="range" min="5" max="100" value={sampleSize} onChange={e => setSampleSize(parseInt(e.target.value))} className="flex-1 accent-indigo-600" />
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    <select value={personaGroup} onChange={e => setPersonaGroup(e.target.value)} className="w-full px-4 py-3 rounded-xl border border-slate-200 bg-white">
                      <option value="">Select a group...</option>
                      {personaGroups.map(g => <option key={g.name} value={g.name}>{g.name} ({g.persona_count})</option>)}
                    </select>
                  </div>
                )}
              </div>
            )}

            {wizardStep === 3 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <h2 className="text-2xl font-bold text-slate-900">What should we ask?</h2>
                  <p className="text-slate-500">Design your survey questions.</p>
                </div>

                <div className="space-y-3 max-h-[400px] overflow-y-auto pr-2">
                  {questionnaire.map((q, idx) => (
                    <div key={q.id || idx} className="p-4 bg-slate-50 rounded-xl border border-slate-200">
                      <div className="flex gap-3">
                        <span className="font-mono text-xs text-slate-400 mt-3 number">Q{idx + 1}</span>
                        <div className="flex-1 space-y-2">
                          <input type="text" value={q.text} onChange={e => updateQuestion(idx, { text: e.target.value })} className="w-full bg-transparent border-none p-0 focus:ring-0 font-medium placeholder:text-slate-400" placeholder="Enter question..." />
                          <select value={q.intent} onChange={e => updateQuestion(idx, { intent: e.target.value })} className="text-xs bg-white border border-slate-200 rounded px-2 py-1">
                            <option value="purchase_intent">Purchase Intent</option>
                            <option value="value_for_money">Value for Money</option>
                            <option value="relevance">Relevance</option>
                            <option value="trust">Trust</option>
                            <option value="clarity">Clarity</option>
                            <option value="differentiation">Differentiation</option>
                          </select>
                        </div>
                        <button onClick={() => removeQuestion(idx)} className="text-slate-400 hover:text-red-500">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-slate-100">
                  <label className="text-sm text-indigo-600 font-medium cursor-pointer flex items-center gap-2 hover:bg-indigo-50 px-3 py-2 rounded-lg transition-colors">
                    <Upload className="w-4 h-4" /> Import CSV
                    <input type="file" className="hidden" accept=".csv" onChange={handleImportQuestions} />
                  </label>
                  <button onClick={addQuestion} className="bg-indigo-100 text-indigo-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-200">+ Add Question</button>
                </div>
              </div>
            )}

            {wizardStep === 4 && (
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <h2 className="text-2xl font-bold text-slate-900">Ready to Launch?</h2>
                  <p className="text-slate-500">Review your configuration before starting the simulation.</p>
                </div>

                <div className="bg-slate-50 rounded-xl p-6 space-y-4">
                  <div>
                    <span className="block text-xs font-bold text-slate-400 uppercase tracking-wider">Product</span>
                    <p className="font-medium text-slate-900">{title}</p>
                    <p className="text-sm text-slate-500">{price}</p>
                  </div>
                  <div>
                    <span className="block text-xs font-bold text-slate-400 uppercase tracking-wider">Audience</span>
                    <p className="font-medium text-slate-900">{populationMode === 'generate' ? `${sampleSize} AI Personas` : `Saved Group: ${personaGroup}`}</p>
                  </div>
                  <div>
                    <span className="block text-xs font-bold text-slate-400 uppercase tracking-wider">Survey</span>
                    <p className="font-medium text-slate-900">{questionnaire.length} Questions</p>
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="bg-slate-50 px-8 py-4 border-t border-slate-200 flex justify-between items-center">
            <button
              onClick={() => setWizardStep(s => Math.max(1, s - 1))}
              disabled={wizardStep === 1}
              className="px-6 py-2.5 rounded-xl font-medium text-slate-600 hover:bg-white hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              Back
            </button>

            {wizardStep < 4 ? (
              <button
                onClick={() => setWizardStep(s => Math.min(4, s + 1))}
                className="px-8 py-2.5 rounded-xl font-medium bg-indigo-600 text-white shadow-lg shadow-indigo-200 hover:shadow-indigo-300 hover:-translate-y-0.5 transition-all"
              >
                Continue
              </button>
            ) : (
              <button
                onClick={() => { handleSimulate(); setViewMode('dashboard'); }}
                disabled={loading}
                className="px-8 py-2.5 rounded-xl font-medium bg-indigo-600 text-white shadow-lg shadow-indigo-200 hover:shadow-indigo-300 hover:-translate-y-0.5 transition-all flex items-center gap-2"
              >
                {loading ? <Loader2 className="animate-spin w-5 h-5" /> : <Play className="w-5 h-5" />}
                Run Simulation
              </button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div
      className="min-h-screen bg-slate-50 text-slate-900 font-sans"
      onKeyDown={(e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
          if (!loading && !previewing && providers.length > 0 && hasValidQuestion && (populationMode !== 'generate' || populationDescription)) {
            handleSimulate();
          }
        }
      }}
    >
      {/* Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="bg-indigo-600 p-2 rounded-lg">
              <LayoutDashboard className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-indigo-600 to-violet-600">
              Synthetic Consumer Research
            </h1>
          </div>
          <div className="flex items-center gap-4 text-sm text-slate-500">
            <div className="bg-slate-100 p-1 rounded-lg flex items-center mr-2">
              <button
                onClick={() => setViewMode('wizard')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${viewMode === 'wizard' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Wizard
              </button>
              <button
                onClick={() => setViewMode('dashboard')}
                className={`px-3 py-1.5 text-xs font-medium rounded-md transition-all ${viewMode === 'dashboard' ? 'bg-white text-indigo-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                Dashboard
              </button>
            </div>
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              System Online
            </span>
            <button
              onClick={() => setShowHistory((prev) => !prev)}
              className={`p-2 rounded-lg transition-colors ${showHistory ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-slate-100 text-slate-500'}`}
              title={showHistory ? 'Hide Run History' : 'Show Run History'}
            >
              <History className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        {viewMode === 'wizard' ? (
          renderWizard()
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Left Column: Configuration */}
            <div className="lg:col-span-4 space-y-6 lg:sticky lg:top-20 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto lg:pr-2 custom-scrollbar">
              <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
                  <h2 className="font-semibold text-slate-800 flex items-center gap-2">
                    <Settings className="w-4 h-4" />
                    Configuration
                  </h2>
                </div>

                {/* Tabs */}
                <div className="flex border-b border-slate-200">
                  <button
                    onClick={() => setActiveTab('basic')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'basic' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                  >
                    Basic
                  </button>
                  <button
                    onClick={() => setActiveTab('population')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'population' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                  >
                    Population
                  </button>
                  <button
                    onClick={() => setActiveTab('advanced')}
                    className={`flex-1 py-3 text-sm font-medium border-b-2 transition-colors ${activeTab === 'advanced' ? 'border-indigo-600 text-indigo-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                  >
                    Advanced
                  </button>
                </div>

                <div className="p-5 space-y-6">

                  {/* BASIC TAB */}
                  {activeTab === 'basic' && (
                    <>
                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Product Concept
                        </label>
                        <input
                          type="text"
                          value={title}
                          onChange={(e) => setTitle(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                          placeholder="Product Name"
                        />
                        <textarea
                          value={description}
                          onChange={(e) => setDescription(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-24 resize-none"
                          placeholder="Describe the product..."
                        />
                        <input
                          type="text"
                          value={price}
                          onChange={(e) => setPrice(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                          placeholder="Price (e.g. $19.99)"
                        />
                      </div>

                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Sample Size
                        </label>
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="5"
                            max="100"
                            step="5"
                            value={sampleSize}
                            onChange={(e) => setSampleSize(parseInt(e.target.value))}
                            className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                          />
                          <span className="text-sm font-mono font-medium text-slate-600 w-8 text-right">
                            {sampleSize}
                          </span>
                        </div>
                      </div>

                      <div className="space-y-3">
                        <div className="flex items-center justify-between">
                          <label className="block text-sm font-medium text-slate-700">
                            Questions
                          </label>
                          <div className="flex items-center gap-3">
                            <label className="text-xs font-medium text-slate-500 hover:text-indigo-600 cursor-pointer flex items-center gap-1 transition-colors">
                              <Upload className="w-3 h-3" />
                              Import CSV
                              <input
                                type="file"
                                accept=".csv,.txt"
                                className="hidden"
                                onChange={handleImportQuestions}
                              />
                            </label>
                            <button
                              onClick={addQuestion}
                              className="text-sm font-medium text-indigo-600 hover:text-indigo-700"
                              type="button"
                            >
                              + Add
                            </button>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {questionnaire.map((q, idx) => (
                            <div
                              key={q.id || idx}
                              className="p-3 rounded-lg border border-slate-200 bg-slate-50"
                            >
                              <div className="flex items-center justify-between gap-3 mb-2">
                                <select
                                  value={q.intent || 'purchase_intent'}
                                  onChange={(e) =>
                                    updateQuestion(idx, { intent: e.target.value })
                                  }
                                  className="px-2.5 py-2 rounded-lg border border-slate-200 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                >
                                  <option value="purchase_intent">Purchase intent</option>
                                  <option value="trust">Trust</option>
                                  <option value="clarity">Clarity</option>
                                  <option value="value_for_money">Value for money</option>
                                  <option value="differentiation">Differentiation</option>
                                  <option value="relevance">Relevance</option>
                                </select>
                                {idx > 0 && (
                                  <button
                                    onClick={() => removeQuestion(idx)}
                                    className="text-xs text-slate-500 hover:text-slate-700"
                                    type="button"
                                  >
                                    Remove
                                  </button>
                                )}
                              </div>
                              <textarea
                                value={q.text}
                                onChange={(e) => updateQuestion(idx, { text: e.target.value })}
                                className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-20 resize-none bg-white"
                                placeholder="Type a question..."
                              />
                            </div>
                          ))}
                        </div>

                        <p className="text-xs text-slate-500">
                          Each question can measure a different construct (intent). The
                          system scores answers against intent-specific anchor banks.
                        </p>
                      </div>
                    </>
                  )}

                  {/* POPULATION TAB */}
                  {activeTab === 'population' && (
                    <div className="space-y-4">
                      <div className="flex gap-2 p-1 bg-slate-100 rounded-lg">
                        <button
                          onClick={() => setPopulationMode('library')}
                          className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${populationMode === 'library' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                          Library
                        </button>
                        <button
                          onClick={() => setPopulationMode('generate')}
                          className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-all ${populationMode === 'generate' ? 'bg-white shadow-sm text-indigo-600' : 'text-slate-500 hover:text-slate-700'}`}
                        >
                          Generate (New)
                        </button>
                      </div>

                      {populationMode === 'library' ? (
                        <div className="space-y-4">
                          <div className="space-y-2">
                            <label className="block text-sm font-medium text-slate-700">
                              Target Audience Group
                            </label>
                            <select
                              value={personaGroup}
                              onChange={(e) => setPersonaGroup(e.target.value)}
                              disabled={personaGroupsLoading || personaGroups.length === 0}
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none bg-white"
                            >
                              {personaGroups.map((group) => (
                                <option key={group.name} value={group.name}>
                                  {personaGroupLabel(group)}
                                </option>
                              ))}
                            </select>
                            <p className="text-xs text-slate-500">
                              {personaGroupsLoading
                                ? 'Loading persona groups...'
                                : selectedGroup
                                  ? `${selectedGroup.description || 'Library group'}`
                                  : 'Pre-defined demographic groups from the library.'}
                            </p>
                          </div>

                          {/* Audience Builder Section */}
                          <div className="p-4 rounded-lg border border-dashed border-indigo-300 bg-indigo-50/50">
                            <div className="flex items-center gap-2 mb-3">
                              <Upload className="w-4 h-4 text-indigo-600" />
                              <h4 className="text-sm font-medium text-indigo-700">Build Audience from Files</h4>
                            </div>
                            <p className="text-xs text-slate-600 mb-3">
                              Upload CSV, PDF, or text files with audience data. We'll generate a representative panel from your evidence.
                            </p>
                            <input
                              ref={fileInputRef}
                              type="file"
                              multiple
                              accept=".csv,.json,.pdf,.txt"
                              onChange={handleFileSelect}
                              className="hidden"
                              id="audience-files"
                            />
                            <div className="flex gap-2 flex-wrap mb-3">
                              <label
                                htmlFor="audience-files"
                                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border border-indigo-200 bg-white text-indigo-600 hover:bg-indigo-50 cursor-pointer transition-colors"
                              >
                                <FileText className="w-4 h-4" />
                                {audienceFiles.length > 0 ? `${audienceFiles.length} files selected` : 'Choose Files'}
                              </label>
                              {audienceFiles.length > 0 && (
                                <button
                                  type="button"
                                  onClick={() => setAudienceFiles([])}
                                  className="px-3 py-2 text-sm text-slate-500 hover:text-slate-700"
                                >
                                  Clear
                                </button>
                              )}
                            </div>
                            {audienceFiles.length > 0 && (
                              <div className="text-xs text-slate-500 mb-3">
                                {audienceFiles.map((f) => f.name).join(', ')}
                              </div>
                            )}
                            <textarea
                              placeholder="Optional: Describe your target audience (e.g., 'Health-conscious moms in urban areas')"
                              value={audienceDescription}
                              onChange={(e) => setAudienceDescription(e.target.value)}
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none text-sm mb-3"
                              rows={2}
                            />
                            <button
                              type="button"
                              onClick={handleBuildAudience}
                              disabled={audienceBuilding || audienceFiles.length === 0}
                              className="w-full py-2 px-4 rounded-lg text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                            >
                              {audienceBuilding ? (
                                <>
                                  <Loader2 className="w-4 h-4 animate-spin" />
                                  Building Audience...
                                </>
                              ) : (
                                <>
                                  <Users className="w-4 h-4" />
                                  Build Audience
                                </>
                              )}
                            </button>
                            {audienceResult && (
                              <div className="mt-3 p-3 rounded-lg bg-green-50 border border-green-200">
                                <div className="flex items-center gap-2 text-green-700 text-sm font-medium mb-2">
                                  <CheckCircle2 className="w-4 h-4" />
                                  Audience Generated
                                </div>
                                <p className="text-xs text-slate-600">{audienceResult.reasoning}</p>
                              </div>
                            )}
                          </div>

                          <div className="p-3 rounded-lg border border-slate-200 bg-slate-50">
                            <div className="flex items-start gap-3">
                              <input
                                type="checkbox"
                                checked={boostEnabled}
                                onChange={(e) => setBoostEnabled(e.target.checked)}
                                className="mt-1 h-4 w-4 accent-indigo-600"
                              />
                              <div className="flex-1">
                                <p className="text-sm font-medium text-slate-700">
                                  Mix-in niche audience
                                </p>
                                <p className="text-xs text-slate-500">
                                  Blend a behavioral segment into the base audience, then compare runs without rebuilding your panel.
                                </p>
                              </div>
                            </div>

                            {boostEnabled && (
                              <div className="mt-3 space-y-3">
                                <textarea
                                  value={boostPrompt}
                                  onChange={(e) => setBoostPrompt(e.target.value)}
                                  className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-24 resize-none bg-white"
                                  placeholder="e.g. Eco-conscious parents who buy premium, read labels, and share recommendations in group chats..."
                                />
                                <div className="space-y-2">
                                  <div className="flex items-center justify-between">
                                    <label className="block text-xs font-medium text-slate-600">
                                      Mix-in share
                                    </label>
                                    <span className="text-xs font-mono font-medium text-slate-600">
                                      {Math.round(boostShare * 100)}%
                                    </span>
                                  </div>
                                  <input
                                    type="range"
                                    min="0"
                                    max="100"
                                    step="5"
                                    value={Math.round(boostShare * 100)}
                                    onChange={(e) =>
                                      setBoostShare(
                                        Math.min(
                                          Math.max(parseInt(e.target.value || '30', 10) / 100, 0),
                                          1
                                        )
                                      )
                                    }
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                                  />
                                  <p className="text-xs text-slate-500">
                                    Each generated persona contributes about{' '}
                                    {(boostCount > 0
                                      ? (boostShare * 100) / boostCount
                                      : 0
                                    ).toFixed(0)}
                                    % of the total panel weight.
                                  </p>
                                </div>
                                <div className="grid grid-cols-2 gap-3">
                                  <div className="space-y-1">
                                    <label className="block text-xs font-medium text-slate-600">
                                      Personas
                                    </label>
                                    <input
                                      type="number"
                                      min="1"
                                      max="20"
                                      step="1"
                                      value={boostCount}
                                      onChange={(e) =>
                                        setBoostCount(parseInt(e.target.value || '2', 10) || 2)
                                      }
                                      className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all bg-white"
                                    />
                                  </div>
                                  <div className="space-y-1">
                                    <label className="block text-xs font-medium text-slate-600">
                                      Strategy
                                    </label>
                                    <select
                                      value={boostStrategy}
                                      onChange={(e) =>
                                        setBoostStrategy(e.target.value as 'heuristic' | 'openai')
                                      }
                                      className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                                    >
                                      <option value="openai">OpenAI</option>
                                      <option value="heuristic">Heuristic</option>
                                    </select>
                                  </div>
                                </div>
                                <p className="text-xs text-slate-500">
                                  Tip: keep a stable Panel Seed (Advanced tab) if you want to compare runs without panel drift.
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          <label className="block text-sm font-medium text-slate-700">
                            Describe Your Audience
                          </label>
                          <textarea
                            value={populationDescription}
                            onChange={(e) => setPopulationDescription(e.target.value)}
                            className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-32 resize-none"
                            placeholder="e.g. Tech-savvy seniors in Florida who play golf..."
                          />
                          <p className="text-xs text-slate-500">
                            The AI will generate unique personas matching this description.
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* ADVANCED TAB */}
                  {activeTab === 'advanced' && (
                    <div className="space-y-6">
                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          AI Providers
                        </label>
                        <div className="grid grid-cols-2 gap-2">
                          {['openai', 'anthropic', 'gemini', 'perplexity'].map((p) => (
                            <button
                              key={p}
                              onClick={() => toggleProvider(p)}
                              className={`px-3 py-2 rounded-lg text-sm font-medium border transition-all capitalize ${providers.includes(p)
                                ? 'bg-indigo-50 border-indigo-200 text-indigo-700'
                                : 'bg-white border-slate-200 text-slate-600 hover:border-slate-300'
                                }`}
                            >
                              {p}
                            </button>
                          ))}
                        </div>
                      </div>

                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Temperature (Creativity)
                        </label>
                        <div className="flex items-center gap-4">
                          <input
                            type="range"
                            min="0"
                            max="2"
                            step="0.1"
                            value={temperature}
                            onChange={(e) => setTemperature(parseFloat(e.target.value))}
                            className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                          />
                          <span className="text-sm font-mono font-medium text-slate-600 w-8 text-right">
                            {temperature}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500">
                          Lower values are more deterministic, higher values are more creative.
                        </p>
                      </div>

                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Additional Instructions / Context
                        </label>
                        <textarea
                          value={additionalInstructions}
                          onChange={(e) => setAdditionalInstructions(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-24 resize-none"
                          placeholder="e.g. Assume a recession economy, or that users are in a rush..."
                        />
                      </div>

                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Panel Seed
                        </label>
                        <input
                          type="number"
                          min="0"
                          value={panelSeed}
                          onChange={(e) => setPanelSeed(parseInt(e.target.value || '0', 10) || 0)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                          placeholder="0"
                        />
                        <p className="text-xs text-slate-500">
                          Keep this stable to reconvene the same synthetic panel across runs.
                        </p>
                      </div>

                      <div className="space-y-3">
                        <label className="block text-sm font-medium text-slate-700">
                          Behavioral Context Pool (Optional)
                        </label>
                        <textarea
                          value={panelContextText}
                          onChange={(e) => setPanelContextText(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all h-28 resize-none"
                          placeholder="Paste notes, bullets, or even a rough 'browser history' profile. We'll split it into chunks and attach a few to each panelist."
                        />
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-1">
                            <label className="block text-xs font-medium text-slate-600">
                              Allocation
                            </label>
                            <select
                              value={panelContextMode}
                              onChange={(e) =>
                                setPanelContextMode(
                                  e.target.value as 'shared' | 'round_robin' | 'sample'
                                )
                              }
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                            >
                              <option value="shared">Give to everyone</option>
                              <option value="round_robin">Distribute evenly</option>
                              <option value="sample">Random assignment</option>
                            </select>
                          </div>
                          <div className="space-y-1">
                            <label className="block text-xs font-medium text-slate-600">
                              Chunks per panelist
                            </label>
                            <input
                              type="number"
                              min="0"
                              max="10"
                              value={panelContextChunksPerPersona}
                              onChange={(e) =>
                                setPanelContextChunksPerPersona(
                                  parseInt(e.target.value || '0', 10) || 0
                                )
                              }
                              className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition-all"
                            />
                          </div>
                        </div>
                        <p className="text-xs text-slate-500">
                          Use bullets or paragraphs. “Give to everyone” applies the same context to every persona.
                          “Distribute evenly” rotates chunks across personas, and “Random assignment” diversifies.
                        </p>
                      </div>

                      <div className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50">
                        <input
                          type="checkbox"
                          checked={includeRespondents}
                          onChange={(e) => setIncludeRespondents(e.target.checked)}
                          className="mt-1 h-4 w-4 accent-indigo-600"
                        />
                        <div>
                          <p className="text-sm font-medium text-slate-700">
                            Include respondent-level data
                          </p>
                          <p className="text-xs text-slate-500">
                            Adds a respondent table to the JSON response for deeper analysis
                            across questions.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="space-y-2">
                    <button
                      onClick={handlePreviewPanel}
                      disabled={
                        previewing ||
                        loading ||
                        providers.length === 0 ||
                        !hasValidQuestion ||
                        (populationMode === 'generate' && !populationDescription)
                      }
                      className="w-full bg-white hover:bg-slate-50 disabled:bg-slate-100 disabled:text-slate-400 disabled:cursor-not-allowed text-slate-700 py-2.5 rounded-lg font-medium transition-all flex items-center justify-center gap-2 border border-slate-200"
                      type="button"
                    >
                      {previewing ? (
                        <>
                          <Loader2 className="w-4 h-4 animate-spin" />
                          Previewing...
                        </>
                      ) : (
                        <>Preview Panel</>
                      )}
                    </button>

                    <button
                      onClick={handleSimulate}
                      disabled={
                        loading ||
                        providers.length === 0 ||
                        !hasValidQuestion ||
                        (populationMode === 'generate' && !populationDescription)
                      }
                      className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg transform active:scale-[0.98]"
                      type="button"
                    >
                      {loading ? (
                        <>
                          <Loader2 className="w-5 h-5 animate-spin" />
                          Running Simulation...
                        </>
                      ) : (
                        <>
                          <Play className="w-5 h-5 fill-current" />
                          Run Simulation
                        </>
                      )}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Column: Results */}
            <div className="lg:col-span-8 space-y-6">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
                  <AlertCircle className="w-5 h-5" />
                  {error}
                </div>
              )}


              {(showHistory) && (
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                  <div className="flex items-center gap-2 mb-4 pb-4 border-b border-slate-100">
                    <History className="w-5 h-5 text-indigo-600" />
                    <h3 className="font-semibold text-slate-800">Run History</h3>
                  </div>

                  <div className="space-y-6">
                    {/* Local History */}
                    {runHistory.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Session</span>
                        </div>
                        {runHistory
                          .slice()
                          .reverse()
                          .map((item) => {
                            const isCurrent = item.id === currentRunId;
                            return (
                              <div
                                key={item.id}
                                className={`flex items-center justify-between gap-3 p-3 rounded-lg border ${isCurrent ? 'border-indigo-200 bg-indigo-50/40' : 'border-slate-200 bg-white'}`}
                              >
                                <button
                                  type="button"
                                  onClick={() => loadRun(item.id)}
                                  className="text-left flex-1"
                                >
                                  <p className="text-sm font-medium text-slate-800">
                                    {item.label}
                                  </p>
                                  <p className="text-xs text-slate-500">
                                    {formatTimestamp(item.createdAt)}
                                  </p>
                                </button>
                                <button
                                  type="button"
                                  onClick={() => deleteRun(item.id)}
                                  className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                  aria-label="Delete run"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            );
                          })}
                      </div>
                    )}

                    {/* Backend History */}
                    {backendRuns.length > 0 && (
                      <div className="space-y-2">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Server</span>
                          <button
                            type="button"
                            onClick={() => loadBackendHistory()}
                            className="ml-auto p-1 text-slate-400 hover:text-slate-600"
                            title="Refresh"
                          >
                            <RefreshCw className={`w-3 h-3 ${loadingHistory ? 'animate-spin' : ''}`} />
                          </button>
                        </div>
                        {backendRuns.map((run) => {
                          const isCurrent = run.id === currentRunId;
                          return (
                            <div
                              key={run.id}
                              className={`flex items-center justify-between gap-3 p-3 rounded-lg border ${isCurrent ? 'border-indigo-200 bg-indigo-50/40' : 'border-slate-200 bg-white'}`}
                            >
                              <button
                                type="button"
                                onClick={() => handleLoadBackendRun(run.id)}
                                className="text-left flex-1"
                              >
                                <p className="text-sm font-medium text-slate-800">
                                  {run.label || 'Untitled Run'}
                                </p>
                                <p className="text-xs text-slate-500">
                                  {new Date(run.created_at).toLocaleString()}
                                </p>
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDeleteBackendRun(run.id)}
                                className="p-2 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                aria-label="Delete run"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}

                    {/* Empty State */}
                    {runHistory.length === 0 && backendRuns.length === 0 && (
                      <div className="text-center py-12 bg-slate-50 rounded-lg border border-slate-100 border-dashed">
                        <History className="w-10 h-10 text-slate-300 mx-auto mb-3" />
                        <p className="text-sm text-slate-500 font-medium">No runs found</p>
                        <p className="text-xs text-slate-400 mt-1">Start a simulation to create history.</p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {panelPreview && !loading && (
                <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-semibold text-slate-800">Panel Preview</h3>
                    <span className="text-xs text-slate-500">
                      {panelPreview.metadata.total_samples || ''} samples
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {panelPreview.panel.slice(0, 6).map((item) => (
                      <div
                        key={item.persona.name}
                        className="p-3 rounded-lg border border-slate-200 bg-slate-50"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <p className="font-medium text-slate-800">{item.persona.name}</p>
                            <p className="text-xs text-slate-500">
                              Weight {(item.persona.weight * 100).toFixed(0)}%
                            </p>
                          </div>
                          <div className="text-xs font-medium text-slate-600">
                            draws {item.draws}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {panelPreview.panel.length > 6 && (
                    <p className="text-xs text-slate-500 mt-3">
                      Showing 6 of {panelPreview.panel.length} personas.
                    </p>
                  )}

                  <div className="mt-5 pt-5 border-t border-slate-100">
                    <h4 className="text-sm font-semibold text-slate-800 mb-2">
                      Questions
                    </h4>
                    <div className="space-y-2">
                      {panelPreview.questions.map((q) => (
                        <div
                          key={q.id || q.text}
                          className="text-sm text-slate-700"
                        >
                          <span className="font-mono text-xs text-slate-500 mr-2">
                            {q.id}
                          </span>
                          {q.text}
                          {q.intent && (
                            <span className="ml-2 text-xs text-indigo-600">
                              ({q.intent})
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {!activeResult && !loading && !panelPreview && (
                <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
                  <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                    <Users className="w-8 h-8 text-indigo-200" />
                  </div>
                  <p className="text-lg font-medium text-slate-500">Ready to simulate</p>
                  <p className="text-sm">Configure your research parameters to begin</p>
                </div>
              )}

              {activeResult && (
                <>
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <div className="flex items-start justify-between gap-4 flex-wrap">
                      <div>
                        <h3 className="font-semibold text-slate-800">Run Workbench</h3>
                        <p className="text-xs text-slate-500 mt-1">
                          {currentRun
                            ? `${currentRun.label} · ${formatTimestamp(currentRun.createdAt)}`
                            : 'Ad hoc result'}
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {providersForActiveRun.length > 0 ? (
                            <>Providers: {providersForActiveRun.join(', ')}</>
                          ) : null}
                          {observedProviderModels ? (
                            <>
                              {providersForActiveRun.length > 0 ? ' · ' : ''}
                              Models: {observedProviderModels}
                            </>
                          ) : null}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            downloadJson(
                              activeResult,
                              `simulation-${currentRun?.id ?? 'latest'}.json`
                            )
                          }
                          className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-sm font-medium flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Results JSON
                        </button>
                        <button
                          type="button"
                          onClick={handleCopySummary}
                          className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 text-sm font-medium flex items-center gap-2"
                        >
                          <Copy className="w-4 h-4" />
                          {copyState === 'copied'
                            ? 'Copied'
                            : copyState === 'failed'
                              ? 'Copy failed'
                              : 'Copy summary'}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (!respondentCsv) return;
                            downloadBlob(
                              respondentCsv,
                              `respondents-${currentRun?.id ?? 'latest'}.csv`,
                              'text/csv'
                            );
                          }}
                          disabled={!respondentCsv}
                          className="px-3 py-2 rounded-lg border border-slate-200 bg-white disabled:bg-slate-100 disabled:text-slate-400 text-slate-700 hover:bg-slate-50 text-sm font-medium flex items-center gap-2"
                        >
                          <Download className="w-4 h-4" />
                          Respondents CSV
                        </button>
                      </div>
                    </div>

                    {currentRun && !configMatchesCurrentRun && (
                      <div className="mt-4 flex items-start justify-between gap-3 p-3 rounded-lg border border-amber-200 bg-amber-50">
                        <div className="flex items-start gap-2">
                          <AlertCircle className="w-4 h-4 text-amber-700 mt-0.5" />
                          <p className="text-xs text-amber-900">
                            Viewing saved run results. Configuration on the left differs.
                          </p>
                        </div>
                        <button
                          type="button"
                          onClick={() => restoreConfigFromRun(currentRun)}
                          className="text-xs font-medium text-amber-900 hover:text-amber-950 underline whitespace-nowrap"
                        >
                          Restore config
                        </button>
                      </div>
                    )}

                    <div className="mt-5 flex items-center justify-between gap-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-slate-700">Baseline</span>
                        <select
                          value={baselineRunId ?? ''}
                          onChange={(e) => setBaselineRunId(e.target.value || null)}
                          className="px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
                        >
                          <option value="">None</option>
                          {runHistory
                            .filter((item) => item.id !== currentRunId)
                            .slice()
                            .reverse()
                            .map((item) => (
                              <option key={item.id} value={item.id}>
                                {formatTimestamp(item.createdAt)} · {item.label}
                              </option>
                            ))}
                        </select>
                        {baselineRunId && (
                          <button
                            type="button"
                            onClick={() => setBaselineRunId(null)}
                            className="text-xs font-medium text-slate-500 hover:text-slate-700"
                          >
                            Clear
                          </button>
                        )}
                      </div>
                    </div>


                    {baselineRun?.response && (
                      <div className="mt-5 grid grid-cols-1 md:grid-cols-3 gap-3">
                        {questionAggregatesFor(activeResult)
                          .slice(0, 3)
                          .map((item) => {
                            const base = baselineAggregateMap.get(item.question_id);
                            if (!base) return null;
                            const meanDelta = item.aggregate.mean - base.aggregate.mean;
                            const top2Delta = item.aggregate.top2box - base.aggregate.top2box;
                            const cardTone =
                              meanDelta > 0
                                ? 'border-green-200 bg-green-50/60'
                                : meanDelta < 0
                                  ? 'border-red-200 bg-red-50/60'
                                  : 'border-slate-200 bg-slate-50';
                            const deltaColor =
                              meanDelta > 0
                                ? 'text-green-700 bg-green-50 border-green-200'
                                : meanDelta < 0
                                  ? 'text-red-700 bg-red-50 border-red-200'
                                  : 'text-slate-600 bg-slate-50 border-slate-200';
                            return (
                              <div
                                key={item.question_id}
                                className={`p-3 rounded-lg border ${cardTone}`}
                              >
                                <p className="text-xs text-slate-500 mb-1">
                                  {item.question_id} · {item.intent}
                                </p>
                                <p className="text-sm font-medium text-slate-800 leading-snug line-clamp-2">
                                  {item.question}
                                </p>
                                <div className="mt-2 flex items-center justify-between gap-2">
                                  <div className="text-xs text-slate-600">
                                    Mean {item.aggregate.mean.toFixed(2)} · Top-2{' '}
                                    {(item.aggregate.top2box * 100).toFixed(0)}%
                                  </div>
                                  <div
                                    className={`px-2 py-1 rounded-md border text-xs font-semibold whitespace-nowrap ${deltaColor}`}
                                  >
                                    {meanDelta >= 0 ? '+' : ''}
                                    {meanDelta.toFixed(2)} ·{' '}
                                    {top2Delta >= 0 ? '+' : ''}
                                    {(top2Delta * 100).toFixed(0)}%
                                  </div>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    )}


                  </div>

                  {/* Top Stats */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div
                      className={`p-5 rounded-xl shadow-sm border ${toneForDelta(overallDeltas?.top2Delta)}`}
                    >
                      <p className="text-sm font-medium text-slate-500 mb-1">{intentLabel}</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-indigo-600">
                          {(activeResult.aggregate.top2box * 100).toFixed(0)}%
                        </span>
                        <span className="text-sm text-green-600 font-medium flex items-center">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Top 2 Box
                        </span>
                      </div>
                      {overallDeltas && (
                        <p
                          className={`mt-2 text-xs font-medium ${textForDelta(overallDeltas.top2Delta)}`}
                        >
                          {overallDeltas.top2Delta >= 0 ? '+' : ''}
                          {(overallDeltas.top2Delta * 100).toFixed(0)}% vs baseline
                        </p>
                      )}
                    </div>
                    <div
                      className={`p-5 rounded-xl shadow-sm border ${toneForDelta(overallDeltas?.meanDelta)}`}
                    >
                      <p className="text-sm font-medium text-slate-500 mb-1">Average Rating</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-slate-800">
                          {activeResult.aggregate.mean.toFixed(1)}
                        </span>
                        <span className="text-sm text-slate-400">/ 5.0</span>
                      </div>
                      {overallDeltas && (
                        <p
                          className={`mt-2 text-xs font-medium ${textForDelta(overallDeltas.meanDelta)}`}
                        >
                          {overallDeltas.meanDelta >= 0 ? '+' : ''}
                          {overallDeltas.meanDelta.toFixed(2)} vs baseline
                        </p>
                      )}
                    </div>
                    <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                      <p className="text-sm font-medium text-slate-500 mb-1">Sample Size</p>
                      <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-slate-800">
                          {activeResult.aggregate.sample_n}
                        </span>
                        <span className="text-sm text-slate-400">respondents</span>
                      </div>
                    </div>
                  </div>

                  {/* Chart */}
                  <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                    <h3 className="font-semibold text-slate-800 mb-6">Rating Distribution</h3>
                    <div className="h-64 w-full">
                      <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={chartData}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                          <XAxis
                            dataKey="rating"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#64748b' }}
                          />
                          <YAxis
                            hide
                          />
                          <Tooltip
                            cursor={{ fill: '#f8fafc' }}
                            contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                          />
                          <Bar
                            dataKey="percentage"
                            fill="#4f46e5"
                            radius={[4, 4, 0, 0]}
                            barSize={40}
                          />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>

                  {activeResult.questions && activeResult.questions.length > 1 && (
                    <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                      <h3 className="font-semibold text-slate-800 mb-4">Question Results</h3>
                      <div className="space-y-3">
                        {activeResult.questions.map((q) => (
                          <div
                            key={q.question_id}
                            className="p-3 rounded-lg border border-slate-200 bg-slate-50"
                          >
                            <p className="text-sm font-medium text-slate-800 mb-1">
                              {q.question_id}: {q.question}
                            </p>
                            <p className="text-xs text-slate-600">
                              Mean {q.aggregate.mean.toFixed(2)} • Top-2{' '}
                              {(q.aggregate.top2box * 100).toFixed(0)}% • Intent {q.intent}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Personas */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-slate-800 px-1">Respondent Segments</h3>
                    {activeResult.personas.map((personaResult, idx) => (
                      <div key={idx} className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 transition-all hover:shadow-md">
                        <div className="flex items-start justify-between mb-4">
                          <div>
                            <h4 className="font-bold text-slate-800 text-lg">
                              {personaResult.persona.name}
                            </h4>
                            <p className="text-sm text-slate-500 mt-1">
                              {(personaResult.persona.descriptors || []).join(' • ')}
                            </p>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-bold text-indigo-600">
                              {(personaResult.distribution.top2box * 100).toFixed(0)}%
                            </div>
                            <div className="text-xs text-slate-400 uppercase tracking-wide font-medium">
                              {intentLabel}
                            </div>
                          </div>
                        </div>

                        <div className="space-y-3">
                          {personaResult.rationales.slice(0, 3).map((rationale, rIdx) => (
                            <div key={rIdx} className="flex gap-3 p-3 bg-slate-50 rounded-lg text-sm text-slate-600 leading-relaxed">
                              <div className="min-w-[24px] h-6 rounded-full bg-white border border-slate-200 flex items-center justify-center text-xs font-medium text-slate-400 shadow-sm">
                                {rIdx + 1}
                              </div>
                              {rationale}
                            </div>
                          ))}
                        </div>

                        <div className="mt-4 pt-4 border-t border-slate-100 flex gap-2 overflow-x-auto pb-2">
                          {personaResult.themes.map((theme, tIdx) => (
                            <span key={tIdx} className="px-2.5 py-1 bg-indigo-50 text-indigo-700 text-xs font-medium rounded-full whitespace-nowrap">
                              {theme}
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div >
  );
}

export default App;
