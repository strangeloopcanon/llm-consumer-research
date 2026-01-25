import { useRef, useEffect, useMemo, useState } from 'react';
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
    Settings,
    Upload,
    FileText,
    Loader2,
    Users,
    CheckCircle2,
    AlertCircle,
    Play,
    History,
    Trash2,
    RefreshCw,
    Download,
    Copy,
} from 'lucide-react';
import type {
    SimulationResponse,
    PersonaGroupSummary,
    QuestionSpec,
    RunSummary,
    PanelPreviewResponse,
    AudienceBuildResponse,
    SimulationRequest
} from '../api';
import type { RunRecord, QuestionAggregate } from '../types';
import type { ChangeEvent } from 'react';

export interface DashboardViewProps {
    // Config State
    activeTab: 'basic' | 'population' | 'advanced';
    setActiveTab: (t: 'basic' | 'population' | 'advanced') => void;
    title: string;
    setTitle: (t: string) => void;
    description: string;
    setDescription: (d: string) => void;
    price: string;
    setPrice: (p: string) => void;
    sampleSize: number;
    setSampleSize: (n: number) => void;

    // Questions
    questionnaire: QuestionSpec[];
    updateQuestion: (idx: number, patch: Partial<QuestionSpec>) => void;
    addQuestion: () => void;
    removeQuestion: (idx: number) => void;
    handleImportQuestions: (e: ChangeEvent<HTMLInputElement>) => void;

    // Population
    populationMode: 'library' | 'generate';
    setPopulationMode: (m: 'library' | 'generate') => void;
    personaGroup: string;
    setPersonaGroup: (g: string) => void;
    personaGroups: PersonaGroupSummary[];
    personaGroupsLoading: boolean;

    // Audience Builder
    audienceFiles: File[];
    setAudienceFiles: (f: File[]) => void;
    audienceDescription: string;
    setAudienceDescription: (d: string) => void;
    audienceBuilding: boolean;
    audienceResult: AudienceBuildResponse | null;
    handleBuildAudience: () => void;
    handleFileSelect: (e: ChangeEvent<HTMLInputElement>) => void;
    fileInputRef: React.RefObject<HTMLInputElement>;

    // Advanced - Boost
    boostEnabled: boolean;
    setBoostEnabled: (b: boolean) => void;
    boostPrompt: string;
    setBoostPrompt: (s: string) => void;
    boostShare: number;
    setBoostShare: (n: number) => void;
    boostCount: number;
    setBoostCount: (n: number) => void;
    boostStrategy: 'heuristic' | 'openai';
    setBoostStrategy: (s: 'heuristic' | 'openai') => void;
    populationDescription: string;
    setPopulationDescription: (d: string) => void;

    // Advanced - Settings
    providers: string[];
    setProviders: (p: string[] | ((prev: string[]) => string[])) => void;
    temperature: number;
    setTemperature: (n: number) => void;
    additionalInstructions: string;
    setAdditionalInstructions: (s: string) => void;
    panelSeed: number;
    setPanelSeed: (n: number) => void;
    panelContextText: string;
    setPanelContextText: (s: string) => void;
    panelContextMode: 'shared' | 'round_robin' | 'sample';
    setPanelContextMode: (m: 'shared' | 'round_robin' | 'sample') => void;
    panelContextChunksPerPersona: number;
    setPanelContextChunksPerPersona: (n: number) => void;
    includeRespondents: boolean;
    setIncludeRespondents: (b: boolean) => void;

    // Actions
    handlePreviewPanel: () => void;
    handleSimulate: () => void;
    loading: boolean;
    previewing: boolean;

    // Results / Errors
    error: string | null;
    panelPreview: PanelPreviewResponse | null;
    activeResult: SimulationResponse | null;

    // History
    showHistory: boolean;
    runHistory: RunRecord[];
    backendRuns: RunSummary[];
    currentRunId: string | null;
    loadRun: (id: string) => void;
    deleteRun: (id: string) => void;
    loadBackendHistory: () => void;
    loadingHistory: boolean;
    handleLoadBackendRun: (id: string) => void;
    handleDeleteBackendRun: (id: string) => void;

    // Result Analysis / UI
    currentRun: RunRecord | undefined;
    restoreConfigFromRun: (run: RunRecord) => void;
    baselineRunId: string | null;
    setBaselineRunId: (id: string | null) => void;
    configMatchesCurrentRun: boolean;
}

export function DashboardView(props: DashboardViewProps) {
    const {
        activeTab, setActiveTab, title, setTitle, description, setDescription, price, setPrice, sampleSize, setSampleSize,
        questionnaire, updateQuestion, addQuestion, removeQuestion, handleImportQuestions,
        populationMode, setPopulationMode, personaGroup, setPersonaGroup, personaGroups, personaGroupsLoading,
        audienceFiles, setAudienceFiles, audienceDescription, setAudienceDescription, audienceBuilding, audienceResult, handleBuildAudience, handleFileSelect, fileInputRef,
        boostEnabled, setBoostEnabled, boostPrompt, setBoostPrompt, boostShare, setBoostShare, boostCount, setBoostCount, boostStrategy, setBoostStrategy, populationDescription, setPopulationDescription,
        providers, setProviders, temperature, setTemperature, additionalInstructions, setAdditionalInstructions, panelSeed, setPanelSeed, panelContextText, setPanelContextText, panelContextMode, setPanelContextMode, panelContextChunksPerPersona, setPanelContextChunksPerPersona, includeRespondents, setIncludeRespondents,
        handlePreviewPanel, handleSimulate, loading, previewing,
        error, panelPreview, activeResult,
        showHistory, runHistory, backendRuns, currentRunId, loadRun, deleteRun, loadBackendHistory, loadingHistory, handleLoadBackendRun, handleDeleteBackendRun,
        currentRun, restoreConfigFromRun, baselineRunId, setBaselineRunId, configMatchesCurrentRun
    } = props;

    const resultsRef = useRef<HTMLDivElement>(null);
    const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

    useEffect(() => {
        if (copyState === 'idle') return;
        const timer = window.setTimeout(() => setCopyState('idle'), 1500);
        return () => window.clearTimeout(timer);
    }, [copyState]);

    const copyTextToClipboard = async (text: string): Promise<boolean> => {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            }
        } catch { } // Fallback
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

    const buildRunSummaryText = (response: SimulationResponse): string => {
        const conceptTitle = (currentRun?.request.concept.title ?? title).trim() || 'Untitled concept';
        const audience = currentRun?.request.persona_group || response.metadata?.persona_group || (populationMode === 'library' ? personaGroup : 'generated audience');
        const seed = typeof currentRun?.request.options.seed === 'number' && currentRun.request.options.seed > 0 ? currentRun.request.options.seed : panelSeed > 0 ? panelSeed : 0;
        const providersLabel = providersForActiveRun.join(', ');

        const lines: string[] = [];
        lines.push(`Synthetic consumer research — ${conceptTitle}`);
        lines.push(`Audience: ${audience} · n=${response.aggregate.sample_n}${seed ? ` · seed=${seed}` : ''}${providersLabel ? ` · providers=${providersLabel}` : ''}`);

        for (const item of questionAggregatesFor(response).slice(0, 3)) {
            const base = baselineAggregateMap.get(item.question_id);
            const deltaMean = base ? item.aggregate.mean - base.aggregate.mean : null;
            const deltaTop2 = base ? item.aggregate.top2box - base.aggregate.top2box : null;
            const delta = deltaMean !== null && deltaTop2 !== null ? ` (Δ mean ${deltaMean >= 0 ? '+' : ''}${deltaMean.toFixed(2)}, Δ top2 ${deltaTop2 >= 0 ? '+' : ''}${(deltaTop2 * 100).toFixed(0)}%)` : '';
            lines.push(`${item.question_id} (${item.intent}): mean=${item.aggregate.mean.toFixed(2)}, top2=${(item.aggregate.top2box * 100).toFixed(0)}%${delta}`);
        }
        return lines.join('\n');
    };

    const handleCopySummary = async () => {
        if (!activeResult) return;
        const ok = await copyTextToClipboard(buildRunSummaryText(activeResult));
        setCopyState(ok ? 'copied' : 'failed');
    };

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
        const rows: string[][] = [['respondent_id', 'persona_name', 'persona_weight', 'question_id', 'intent', 'anchor_bank', 'provider', 'model', 'score_mean', 'rationale']];
        let hasRows = false;
        for (const personaResult of response.personas) {
            const personaName = personaResult.persona.name;
            const personaWeight = personaResult.persona.weight ?? 0;
            const respondents = personaResult.respondents || [];
            for (const respondent of respondents) {
                for (const answer of respondent.answers || []) {
                    hasRows = true;
                    rows.push([respondent.respondent_id, personaName, String(personaWeight), answer.question_id, answer.intent, answer.anchor_bank, answer.provider, answer.model, String(answer.score_mean), answer.rationale.replace(/\r?\n/g, ' ').trim()]);
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

    const respondentCsv = useMemo(() => {
        if (!activeResult) return null;
        return flattenRespondentsToCsv(activeResult);
    }, [activeResult]);

    const personaGroupLabel = (group: PersonaGroupSummary) =>
        `${group.name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase())} (${group.persona_count})`;

    // Auto-scroll to results
    useEffect(() => {
        if (activeResult && resultsRef.current && !loading) {
            setTimeout(() => {
                resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }, [activeResult, loading]);

    const toggleProvider = (p: string) => {
        setProviders(prev => prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]);
    };

    const selectedGroup = useMemo(() =>
        personaGroups.find(g => g.name === personaGroup),
        [personaGroups, personaGroup]
    );

    const providersForActiveRun = useMemo(() => {
        const opts = currentRun?.request?.options as any;
        return Array.isArray(opts?.providers) ? opts.providers : [];
    }, [currentRun]);

    const observedProviderModels = useMemo(() => {
        if (!activeResult?.metadata?.provider_models) return null;
        return Object.entries(activeResult.metadata.provider_models)
            .map(([provider, model]) => `${provider}=${model}`)
            .join(', ');
    }, [activeResult]);

    const intentLabel = useMemo(() => {
        if (!activeResult?.questions) return 'Purchase Intent';
        const q1 = activeResult.questions.find(q => q.question_id === 'q1');
        return q1?.intent || 'Purchase Intent';
    }, [activeResult]);

    const chartData = useMemo(() => {
        if (!activeResult) return [];
        const pmf = activeResult.aggregate.pmf;
        return [1, 2, 3, 4, 5].map((r, idx) => ({
            rating: r,
            percentage: Math.round((pmf[idx] || 0) * 100),
        }));
    }, [activeResult]);

    // Baseline Comparison Logic
    const baselineRun = useMemo(() =>
        runHistory.find(r => r.id === baselineRunId),
        [runHistory, baselineRunId]
    );

    const formatTimestamp = (ts: number) => new Date(ts).toLocaleString();

    const questionAggregatesFor = (res: SimulationResponse) =>
        res.questions || [];

    const baselineAggregateMap = useMemo(() => {
        const map = new Map<string, QuestionAggregate>();
        if (!baselineRun?.response?.questions) return map;
        for (const q of baselineRun.response.questions) {
            map.set(q.question_id, q);
        }
        return map;
    }, [baselineRun]);

    const overallDeltas = useMemo(() => {
        if (!activeResult || !baselineRun?.response) return null;
        return {
            meanDelta: activeResult.aggregate.mean - baselineRun.response.aggregate.mean,
            top2Delta: activeResult.aggregate.top2box - baselineRun.response.aggregate.top2box
        };
    }, [activeResult, baselineRun]);

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


    return (
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
            <div className="lg:col-span-8 space-y-6" ref={resultsRef}>
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
                                {backendRuns.length > 0 && backendRuns.map((run) => {
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

                {activeResult && currentRun && (
                    <>
                        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
                            <div className="flex items-start justify-between gap-4 flex-wrap">
                                <div>
                                    <h3 className="font-semibold text-slate-800">Run Workbench</h3>
                                    <p className="text-xs text-slate-500 mt-1">
                                        {currentRun.label} · {formatTimestamp(currentRun.createdAt)}
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
                                                `simulation-${currentRun.id}.json`
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
                                                `respondents-${currentRun.id}.csv`,
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

                            {!configMatchesCurrentRun && (
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
    );
}
