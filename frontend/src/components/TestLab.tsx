import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Code2, BrainCircuit, Wrench, Check } from 'lucide-react';

export default function TestLab({ runId }: { runId: string | null }) {
  const [tests, setTests] = useState<any[]>([]);
  const [selectedTest, setSelectedTest] = useState<any | null>(null);
  const [analysis, setAnalysis] = useState<any | null>(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [patching, setPatching] = useState(false);
  const [patchSuccess, setPatchSuccess] = useState(false);

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/runs/${runId}/tests`)
      .then(res => res.json())
      .then(data => {
        if (data.tests && Array.isArray(data.tests)) {
          setTests(data.tests);
        }
      })
      .catch(console.error);
  }, [runId]);

  const handleTestClick = (test: any) => {
    setSelectedTest(test);
    if (test.status === 'FAIL') {
      setLoadingAnalysis(true);
      setAnalysis(null);
      setPatching(false);
      setPatchSuccess(false);
      fetch(`/api/runs/${runId}/tests/${test.test_id}/analysis`)
        .then(res => res.json())
        .then(data => {
          setAnalysis(data);
          setLoadingAnalysis(false);
        })
        .catch(err => {
          console.error(err);
          setLoadingAnalysis(false);
        });
    }
  };

  const handlePatch = async () => {
    if (!analysis?.suggested_fix) return;
    setPatching(true);
    try {
      const res = await fetch(`/api/runs/${runId}/patch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fix_snippet: analysis.suggested_fix })
      });
      if (res.ok) setPatchSuccess(true);
      else console.error("Patch failed");
    } catch (e) {
      console.error(e);
    }
    setPatching(false);
  };

  return (
    <div className="p-8 h-full flex flex-col gap-6 bg-[#050505] relative">
      <header className="flex justify-between items-end mb-4">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white">Execution Test Lab</h2>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Autonomous Generated Scenarios</p>
        </div>
      </header>

      <div className="flex-1 bg-[#0a0a0a] border border-white/5 rounded-2xl overflow-hidden flex flex-col shadow-[0_0_50px_rgba(59,130,246,0.05)]">
        <div className="overflow-auto flex-1 scrollbar-custom p-2">
          <table className="w-full text-left text-sm whitespace-nowrap border-collapse">
            <thead className="bg-[#111] sticky top-0 z-10 shadow-md">
              <tr>
                <th className="p-4 font-bold text-gray-500 uppercase tracking-widest text-xs border-b border-white/5">ID</th>
                <th className="p-4 font-bold text-gray-500 uppercase tracking-widest text-xs border-b border-white/5">Status</th>
                <th className="p-4 font-bold text-gray-500 uppercase tracking-widest text-xs border-b border-white/5">Target / Boundary</th>
                <th className="p-4 font-bold text-gray-500 uppercase tracking-widest text-xs border-b border-white/5">Risk Category</th>
                <th className="p-4 font-bold text-gray-500 uppercase tracking-widest text-xs border-b border-white/5">AI Hypothesis</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {tests.map(test => (
                <tr key={test.test_id} onClick={() => handleTestClick(test)} className="hover:bg-blue-900/10 transition-colors group cursor-pointer">
                  <td className="p-4 font-mono text-gray-400 group-hover:text-blue-400">{test.test_id}</td>
                  <td className="p-4">
                    <span className={`px-3 py-1 rounded-full text-xs font-bold tracking-widest uppercase border ${
                      test.status === 'PASS' 
                        ? 'bg-green-900/20 text-green-400 border-green-500/30 shadow-[0_0_10px_rgba(34,197,94,0.2)]' 
                        : test.status === 'FAIL' 
                          ? 'bg-red-900/20 text-red-400 border-red-500/30 shadow-[0_0_10px_rgba(239,68,68,0.2)]'
                          : 'bg-gray-900 text-gray-400 border-gray-700'
                    }`}>
                      {test.status}
                    </span>
                  </td>
                  <td className="p-4 font-mono text-blue-300">{test.target}</td>
                  <td className="p-4">
                    <span className="text-xs bg-[#1a1a1a] text-purple-400 px-2 py-1 rounded border border-purple-500/20 font-mono">
                      {test.category}
                    </span>
                  </td>
                  <td className="p-4 text-gray-400 truncate max-w-md">{test.reason}</td>
                </tr>
              ))}
              {tests.length === 0 && (
                <tr>
                  <td colSpan={5} className="p-12 text-center text-gray-600 font-mono">
                    <div className="flex flex-col items-center gap-4">
                      <div className="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                      Awaiting scenario generation...
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <AnimatePresence>
        {selectedTest && (
          <motion.div
            initial={{ opacity: 0, backdropFilter: 'blur(0px)' }}
            animate={{ opacity: 1, backdropFilter: 'blur(12px)' }}
            exit={{ opacity: 0, backdropFilter: 'blur(0px)' }}
            transition={{ duration: 0.3 }}
            className="absolute inset-0 bg-black/70 z-50 flex items-center justify-center p-8"
          >
            <motion.div
              initial={{ scale: 0.9, y: 30, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.95, y: 20, opacity: 0 }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className={`bg-[#080808] border rounded-2xl w-full max-w-4xl max-h-full overflow-hidden flex flex-col shadow-2xl relative ${
                selectedTest.status === 'FAIL' 
                  ? 'border-red-500/30 shadow-[0_0_80px_rgba(239,68,68,0.15)]' 
                  : 'border-green-500/30 shadow-[0_0_80px_rgba(34,197,94,0.15)]'
              }`}
            >
              {/* Top ambient glow */}
              <div className={`absolute top-0 left-0 right-0 h-1 ${
                selectedTest.status === 'FAIL' ? 'bg-gradient-to-r from-red-500/0 via-red-500/50 to-red-500/0' : 'bg-gradient-to-r from-green-500/0 via-green-500/50 to-green-500/0'
              }`}></div>

              <div className="p-6 border-b border-white/5 flex justify-between items-center bg-[#0a0a0a]">
                <div className="flex items-center gap-4">
                  <h3 className="text-2xl font-black text-white font-mono tracking-tight">{selectedTest.test_id}</h3>
                  <span className={`px-4 py-1 rounded-full text-xs font-bold tracking-widest uppercase border shadow-sm ${
                    selectedTest.status === 'FAIL' 
                      ? 'bg-red-900/30 text-red-400 border-red-500/50 shadow-red-500/20' 
                      : 'bg-green-900/30 text-green-400 border-green-500/50 shadow-green-500/20'
                  }`}>
                    {selectedTest.status}
                  </span>
                </div>
                <button onClick={() => setSelectedTest(null)} className="text-gray-500 hover:text-white transition-colors bg-white/5 hover:bg-white/10 rounded-full p-2">
                  <X size={20} />
                </button>
              </div>
              
              <div className="p-8 overflow-auto scrollbar-custom flex-1 space-y-8">
                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-[#0f0f0f] p-5 rounded-xl border border-white/5 shadow-inner">
                    <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">Execution Target</p>
                    <p className="font-mono text-blue-400 text-sm bg-[#151515] p-2 rounded inline-block border border-blue-500/10">{selectedTest.target}</p>
                  </div>
                  <div className="bg-[#0f0f0f] p-5 rounded-xl border border-white/5 shadow-inner">
                    <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2">Risk Category</p>
                    <p className="font-mono text-purple-400 text-sm bg-purple-900/10 px-3 py-1.5 rounded inline-block border border-purple-500/20">{selectedTest.category}</p>
                  </div>
                </div>

                <div className="bg-[#0f0f0f] p-6 rounded-xl border border-white/5 shadow-inner border-l-4 border-l-blue-500/50">
                  <p className="text-xs text-blue-400/70 font-bold uppercase tracking-widest mb-3">AI Agent Hypothesis</p>
                  <p className="text-gray-300 text-sm leading-relaxed">{selectedTest.reason}</p>
                </div>

                {selectedTest.status === 'FAIL' && (
                  <motion.div 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 }}
                    className="bg-blue-950/20 border border-blue-500/20 p-8 rounded-2xl space-y-6 relative overflow-hidden shadow-inner"
                  >
                    <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl -mr-32 -mt-32 pointer-events-none"></div>
                    
                    <div className="flex items-center gap-3 text-blue-400 font-black uppercase tracking-widest text-sm mb-6 pb-4 border-b border-blue-500/10">
                      <BrainCircuit size={20} className="text-blue-500" />
                      Agent Root Cause Analysis
                    </div>
                    
                    {loadingAnalysis ? (
                      <div className="flex flex-col items-center justify-center py-16 gap-8 relative overflow-hidden rounded-2xl border border-blue-500/10 bg-black/40 shadow-[inset_0_0_50px_rgba(59,130,246,0.05)]">
                        <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.05)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.05)_1px,transparent_1px)] bg-[size:20px_20px] [mask-image:radial-gradient(ellipse_50%_50%_at_50%_50%,#000_70%,transparent_100%)] opacity-30"></div>
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cyan-500 to-transparent opacity-50 animate-[shimmer_2s_infinite]"></div>
                        
                        <div className="relative z-10">
                          <div className="absolute inset-0 bg-cyan-500/20 blur-2xl rounded-full animate-pulse"></div>
                          <div className="relative w-24 h-24 border border-blue-500/20 rounded-full flex items-center justify-center bg-blue-950/30 backdrop-blur-sm">
                            <div className="absolute inset-0 border-t-2 border-cyan-400 rounded-full animate-[spin_2s_linear_infinite]"></div>
                            <div className="absolute inset-2 border-r-2 border-blue-400/50 rounded-full animate-[spin_3s_linear_infinite_reverse]"></div>
                            <BrainCircuit size={36} className="text-cyan-400 animate-pulse drop-shadow-[0_0_10px_rgba(34,211,238,0.5)]" />
                          </div>
                        </div>
                        
                        <div className="flex flex-col items-center gap-4 text-center relative z-10">
                          <p className="text-cyan-300 font-mono text-sm tracking-[0.2em] uppercase font-bold bg-blue-900/30 px-6 py-2 rounded-full border border-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.1)]">
                            Neural Analysis Active
                          </p>
                          <div className="text-cyan-100/60 text-xs font-mono space-y-2 mt-2">
                            <p className="animate-[pulse_1s_infinite]">&gt; Injecting execution state into LLM context window...</p>
                            <p className="animate-[pulse_1s_infinite_100ms] opacity-70">&gt; Correlating memory faults with AST boundaries...</p>
                            <p className="animate-[pulse_1s_infinite_200ms] opacity-50">&gt; Synthesizing vulnerability remediation payload...</p>
                          </div>
                        </div>
                      </div>
                    ) : analysis ? (
                      <motion.div 
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="space-y-8"
                      >
                        <div>
                          <h4 className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-3">Vulnerability Explanation</h4>
                          <p className="text-gray-200 text-sm leading-relaxed bg-black/40 p-5 rounded-xl border border-white/5 shadow-inner">
                            {analysis.analysis}
                          </p>
                        </div>
                        
                        <div>
                          <div className="flex items-center justify-between mb-3">
                            <div className="flex items-center gap-2 text-emerald-400 font-bold uppercase tracking-widest text-xs">
                              <Code2 size={16} />
                              Suggested Remediation Patch
                            </div>
                            <button 
                              onClick={handlePatch}
                              disabled={patching || patchSuccess}
                              className={`flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                                patchSuccess 
                                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50' 
                                  : 'bg-emerald-500 text-black hover:bg-emerald-400 hover:scale-105 shadow-[0_0_15px_rgba(16,185,129,0.4)]'
                              }`}
                            >
                              {patchSuccess ? (
                                <>
                                  <Check size={14} /> Patch Applied
                                </>
                              ) : patching ? (
                                <>
                                  <div className="w-3 h-3 border-2 border-black/30 border-t-black rounded-full animate-spin"></div>
                                  Patching...
                                </>
                              ) : (
                                <>
                                  <Wrench size={14} /> Auto-Patch Codebase
                                </>
                              )}
                            </button>
                          </div>
                          <div className="relative group">
                            <div className="absolute -inset-0.5 bg-gradient-to-r from-emerald-500/20 to-blue-500/20 rounded-xl blur opacity-30 group-hover:opacity-60 transition duration-500"></div>
                            <pre className="relative bg-[#050505] p-5 rounded-xl overflow-x-auto border border-white/10 font-mono text-xs text-emerald-400/90 shadow-2xl">
                              <code>{analysis.suggested_fix}</code>
                            </pre>
                          </div>
                        </div>
                      </motion.div>
                    ) : (
                      <p className="text-gray-500 text-sm italic py-8 text-center bg-black/20 rounded-xl border border-white/5">Failed to fetch analysis payload.</p>
                    )}
                  </motion.div>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
