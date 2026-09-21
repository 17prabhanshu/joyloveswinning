import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, CheckCircle, XCircle } from 'lucide-react';

export default function Simulators({ runId }: { runId: string | null }) {
  const [simulators, setSimulators] = useState<any[]>([]);

  useEffect(() => {
    fetch('/api/simulators')
      .then(res => res.json())
      .then(data => setSimulators(data.simulators || []))
      .catch(console.error);
  }, []);

  return (
    <div className="p-8 h-full bg-[#050505]">
      <div className="mb-8">
        <h2 className="text-3xl font-black tracking-tighter text-white">Execution Engines</h2>
        <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Hardware Emulation & Simulation Adapters</p>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {simulators.map((sim, i) => (
          <motion.div 
            key={i}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className="bg-[#0a0a0a] border border-white/5 rounded-2xl p-6 shadow-2xl relative overflow-hidden group hover:border-blue-500/30 transition-colors"
          >
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-3">
                <div className="p-3 bg-blue-900/20 text-blue-400 rounded-xl border border-blue-500/30">
                  <Cpu size={24} />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{sim.name}</h3>
                  <p className="text-gray-500 text-sm font-mono">v{sim.version}</p>
                </div>
              </div>
              <div className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-widest flex items-center gap-2 ${sim.available ? 'bg-green-900/20 text-green-400 border border-green-500/30' : 'bg-red-900/20 text-red-400 border border-red-500/30'}`}>
                {sim.available ? <CheckCircle size={14} /> : <XCircle size={14} />}
                {sim.status}
              </div>
            </div>
            
            <div className="bg-[#111] rounded-lg p-4 font-mono text-sm text-gray-400 border border-white/5 mb-4">
              <p><span className="text-gray-600">Backend:</span> {sim.backend}</p>
              <p><span className="text-gray-600">Adapter Loaded:</span> YES</p>
              <p><span className="text-gray-600">Health Check:</span> {sim.available ? 'PASSED' : 'FAILED - Binary not in PATH'}</p>
            </div>
            
            <button 
              onClick={() => fetch(`/api/simulators/${sim.name}/launch`, { 
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ run_id: runId })
              })}
              className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold font-mono tracking-widest uppercase rounded-lg transition-colors border border-blue-400/50 shadow-[0_0_15px_rgba(37,99,235,0.3)]"
            >
              &gt;_ Launch Interactive Shell
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
