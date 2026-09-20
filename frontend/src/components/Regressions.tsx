import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { GitMerge, ShieldCheck } from 'lucide-react';

export default function Regressions({ runId }: { runId: string | null }) {
  const [regressions, setRegressions] = useState<any[]>([]);

  useEffect(() => {
    if (!runId) return;
    const fetchRegressions = () => {
      fetch(`/api/runs/${runId}/regressions`)
        .then(res => res.json())
        .then(data => setRegressions(data.regressions || []))
        .catch(console.error);
    };
    
    fetchRegressions();
    const interval = setInterval(fetchRegressions, 2000);
    return () => clearInterval(interval);
  }, [runId]);

  return (
    <div className="p-8 h-full bg-[#050505] flex flex-col">
      <div className="mb-8 flex justify-between items-end">
        <div>
          <h2 className="text-3xl font-black tracking-tighter text-white">Regression Vault</h2>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Autonomously Minimized Failure Scenarios</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2 bg-green-900/20 border border-green-500/30 rounded-full text-green-400 text-xs font-bold tracking-widest uppercase shadow-[0_0_15px_rgba(34,197,94,0.3)]">
          <ShieldCheck size={14} /> CI/CD Ready
        </div>
      </div>

      <div className="flex-1 overflow-auto space-y-4 pr-2 scrollbar-custom">
        {regressions.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-gray-600 font-mono gap-4">
            <GitMerge size={48} className="opacity-50" />
            <p>No regressions mapped yet.</p>
          </div>
        ) : (
          regressions.map((r, i) => (
            <motion.div 
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              className="bg-[#0a0a0a] border border-white/5 hover:border-green-500/30 transition-colors rounded-2xl p-6"
            >
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <GitMerge size={18} className="text-green-500" /> 
                    {r.regression_id}
                  </h3>
                  <p className="text-gray-400 text-sm mt-1">Target: <span className="font-mono text-blue-400">{r.scenario?.target}</span></p>
                </div>
                <span className="text-xs font-mono text-gray-500">{new Date(r.created_at).toLocaleString()}</span>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-[#111] p-4 rounded-lg border border-red-500/20">
                  <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2 text-red-500">Observed Failure</p>
                  <p className="font-mono text-sm text-gray-300">{r.observed_failure}</p>
                </div>
                <div className="bg-[#111] p-4 rounded-lg border border-green-500/20">
                  <p className="text-xs text-gray-500 font-bold uppercase tracking-widest mb-2 text-green-500">Expected Behavior</p>
                  <p className="font-mono text-sm text-gray-300">{r.expected_behavior}</p>
                </div>
              </div>
            </motion.div>
          ))
        )}
      </div>
    </div>
  );
}
