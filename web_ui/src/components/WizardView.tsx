import { Play, Loader2, Upload, Trash2 } from 'lucide-react';
import type { QuestionSpec, PersonaGroupSummary } from '../api';
import type { ChangeEvent } from 'react';

// Define props for WizardView
export interface WizardViewProps {
    setViewMode: (mode: 'dashboard' | 'wizard') => void;
    wizardStep: number;
    setWizardStep: (step: number | ((prev: number) => number)) => void;
    title: string;
    setTitle: (t: string) => void;
    description: string;
    setDescription: (d: string) => void;
    price: string;
    setPrice: (p: string) => void;
    populationMode: 'library' | 'generate';
    setPopulationMode: (m: 'library' | 'generate') => void;
    personaGroup: string;
    setPersonaGroup: (g: string) => void;
    populationDescription: string;
    setPopulationDescription: (d: string) => void;
    sampleSize: number;
    setSampleSize: (n: number) => void;
    personaGroups: PersonaGroupSummary[];
    questionnaire: QuestionSpec[];
    updateQuestion: (idx: number, patch: Partial<QuestionSpec>) => void;
    addQuestion: () => void;
    removeQuestion: (idx: number) => void;
    handleImportQuestions: (e: ChangeEvent<HTMLInputElement>) => void;
    loading: boolean;
    handleSimulate: () => void;
}

export function WizardView({
    setViewMode,
    wizardStep,
    setWizardStep,
    title,
    setTitle,
    description,
    setDescription,
    price,
    setPrice,
    populationMode,
    setPopulationMode,
    personaGroup,
    setPersonaGroup,
    populationDescription,
    setPopulationDescription,
    sampleSize,
    setSampleSize,
    personaGroups,
    questionnaire,
    updateQuestion,
    addQuestion,
    removeQuestion,
    handleImportQuestions,
    loading,
    handleSimulate,
}: WizardViewProps) {
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
}
