import React, { useState } from 'react';
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
  MessageSquare,
  ChevronRight,
  AlertCircle,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { runSimulation, type SimulationResponse, type PersonaResult } from './api';

function App() {
  // Form State
  const [title, setTitle] = useState('RadiantSmile Whitening Toothpaste');
  const [description, setDescription] = useState(
    'A professional-grade whitening toothpaste that is safe for daily use. Features enamel-protection technology and a refreshing mint flavor.'
  );
  const [price, setPrice] = useState('$5.99');

  // Population State
  const [populationMode, setPopulationMode] = useState<'library' | 'generate'>('library');
  const [personaGroup, setPersonaGroup] = useState('us_toothpaste_buyers');
  const [populationDescription, setPopulationDescription] = useState('');

  // Advanced State
  const [providers, setProviders] = useState<string[]>(['openai']);
  const [sampleSize, setSampleSize] = useState(50);
  const [temperature, setTemperature] = useState(1.0);
  const [additionalInstructions, setAdditionalInstructions] = useState('');

  // App State
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'basic' | 'population' | 'advanced'>('basic');

  const handleSimulate = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await runSimulation({
        concept: {
          title,
          text: description,
          price,
        },
        persona_group: populationMode === 'library' ? personaGroup : undefined,
        population_spec: populationMode === 'generate' ? {
          generations: [{
            prompt: populationDescription,
            count: sampleSize, // Generate roughly the sample size requested
            strategy: 'openai'
          }]
        } : undefined,
        options: {
          n: sampleSize,
          providers,
          stratified: false,
          temperature,
          additional_instructions: additionalInstructions || undefined,
        },
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Simulation failed');
    } finally {
      setLoading(false);
    }
  };

  const toggleProvider = (p: string) => {
    setProviders((prev) =>
      prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]
    );
  };

  const chartData = result?.aggregate.pmf.map((val, idx) => ({
    rating: idx + 1,
    percentage: (val * 100).toFixed(1),
  }));

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
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
            <span className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-green-500"></div>
              System Online
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Configuration */}
        <div className="lg:col-span-4 space-y-6">
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
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-slate-700">
                        Target Audience Group
                      </label>
                      <select
                        value={personaGroup}
                        onChange={(e) => setPersonaGroup(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-slate-200 focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none bg-white"
                      >
                        <option value="us_toothpaste_buyers">US Toothpaste Buyers</option>
                        <option value="general_population">General Population</option>
                      </select>
                      <p className="text-xs text-slate-500">
                        Pre-defined demographic groups from the library.
                      </p>
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
                </div>
              )}

              <button
                onClick={handleSimulate}
                disabled={loading || providers.length === 0 || (populationMode === 'generate' && !populationDescription)}
                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-2 shadow-md hover:shadow-lg transform active:scale-[0.98]"
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

        {/* Right Column: Results */}
        <div className="lg:col-span-8 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-5 h-5" />
              {error}
            </div>
          )}

          {!result && !loading && (
            <div className="h-full min-h-[400px] flex flex-col items-center justify-center text-slate-400 border-2 border-dashed border-slate-200 rounded-xl bg-slate-50/50">
              <div className="bg-white p-4 rounded-full shadow-sm mb-4">
                <Users className="w-8 h-8 text-indigo-200" />
              </div>
              <p className="text-lg font-medium text-slate-500">Ready to simulate</p>
              <p className="text-sm">Configure your research parameters to begin</p>
            </div>
          )}

          {result && (
            <>
              {/* Top Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                  <p className="text-sm font-medium text-slate-500 mb-1">Purchase Intent</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-indigo-600">
                      {(result.aggregate.top2box * 100).toFixed(0)}%
                    </span>
                    <span className="text-sm text-green-600 font-medium flex items-center">
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Top 2 Box
                    </span>
                  </div>
                </div>
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                  <p className="text-sm font-medium text-slate-500 mb-1">Average Rating</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-slate-800">
                      {result.aggregate.mean.toFixed(1)}
                    </span>
                    <span className="text-sm text-slate-400">/ 5.0</span>
                  </div>
                </div>
                <div className="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
                  <p className="text-sm font-medium text-slate-500 mb-1">Sample Size</p>
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-slate-800">
                      {result.aggregate.sample_n}
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

              {/* Personas */}
              <div className="space-y-4">
                <h3 className="font-semibold text-slate-800 px-1">Respondent Segments</h3>
                {result.personas.map((personaResult, idx) => (
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
                          Purchase Intent
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
      </main>
    </div>
  );
}

export default App;
