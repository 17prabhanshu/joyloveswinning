import { useState, useEffect } from 'react';
import { Activity, ShieldAlert, CheckCircle, XCircle, Zap } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Overview({ runId }: { runId: string | null }) {
  const [events, setEvents] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({ total: 0, passed: 0, failed: 0, risks: 0 });

  useEffect(() => {
    if (!runId) return;

    fetch(`/api/runs/${runId}/tests`)
      .then(res => res.json())
      .then(data => {
        if (data.tests && Array.isArray(data.tests)) {
          const passed = data.tests.filter((t: any) => t.status === 'PASS').length;
          const failed = data.tests.filter((t: any) => t.status === 'FAIL').length;
          setMetrics(m => ({ ...m, total: data.tests.length, passed, failed }));
        }
      }).catch(console.error);

    fetch(`/api/runs/${runId}/risks`)
      .then(res => res.json())
      .then(data => {
        if (data.risks && Array.isArray(data.risks)) {
          setMetrics(m => ({ ...m, risks: data.risks.length }));
        }
      }).catch(console.error);

    const eventSource = new EventSource(`/api/runs/${runId}/events`);
    eventSource.onmessage = (e) => {
      try {
        const eventData = JSON.parse(e.data);
        setEvents(prev => [eventData, ...prev].slice(0, 50));
      } catch (err) {
        console.error(err);
      }
    };

    return () => {
      eventSource.close();
    };
  }, [runId]);

  return (
    <div className="p-8 h-full flex flex-col gap-8 bg-[#050505]">
      <header className="flex justify-between items-end">
        <div>
          <h2 className="text-4xl font-black tracking-tighter bg-gradient-to-r from-white to-gray-600 bg-clip-text text-transparent">Control Console</h2>
          <p className="text-gray-500 text-sm mt-1 uppercase tracking-widest font-mono">Live Telemetry & Diagnostics</p>
        </div>
        <div className="flex gap-4">
          <a href={`/api/runs/${runId}/report`} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-6 py-2 bg-purple-900/20 border border-purple-500/30 rounded-lg text-purple-400 text-sm font-bold tracking-widest uppercase hover:bg-purple-900/40 transition-colors">
            Generate Report
          </a>
          <div className="flex items-center gap-2 px-4 py-2 bg-blue-900/20 border border-blue-500/30 rounded-full text-blue-400 text-xs font-bold tracking-widest uppercase shadow-[0_0_15px_rgba(59,130,246,0.3)]">
            <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></span>
            System Online
          </div>
        </div>
      </header>

      <div className="grid grid-cols-4 gap-6">
        <MetricCard title="TESTS EXECUTED" value={metrics.total} icon={Activity} />
        <MetricCard title="ASSERTIONS PASSED" value={metrics.passed} icon={CheckCircle} color="text-green-500" glow="shadow-[0_0_20px_rgba(34,197,94,0.15)]" />
        <MetricCard title="ANOMALIES FOUND" value={metrics.failed} icon={XCircle} color="text-red-500" glow="shadow-[0_0_20px_rgba(239,68,68,0.15)]" />
        <MetricCard title="HUNTED RISKS" value={metrics.risks} icon={ShieldAlert} color="text-yellow-500" glow="shadow-[0_0_20px_rgba(234,179,8,0.15)]" />
      </div>

      <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
        <div className="col-span-2 bg-[#0a0a0a] border border-white/5 rounded-2xl flex flex-col overflow-hidden shadow-2xl relative">
          <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-blue-500/50 to-transparent"></div>
          <div className="p-5 border-b border-white/5 bg-[#111]/50 backdrop-blur-md">
            <h3 className="font-bold tracking-widest text-xs text-gray-400 uppercase flex items-center gap-3">
              <Zap size={14} className="text-blue-500" /> Activity Stream
            </h3>
          </div>
          <div className="flex-1 overflow-auto p-5 space-y-3 font-mono text-sm scrollbar-custom">
            {events.map((ev, i) => (
              <motion.div key={i} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}>
                <div className="flex gap-4 p-3 bg-black/40 rounded-lg border border-white/5 hover:border-blue-500/30 hover:bg-blue-900/10 transition-colors">
                  <span className="text-gray-600 whitespace-nowrap text-xs flex items-center">{new Date(ev.timestamp || Date.now()).toLocaleTimeString()}</span>
                  <span className="text-blue-400 font-bold w-32 truncate text-xs flex items-center">[{ev.agent || 'SYSTEM'}]</span>
                  <span className="text-gray-300 flex-1 leading-relaxed">{ev.reason || ev.message || JSON.stringify(ev)}</span>
                </div>
              </motion.div>
            ))}
            {events.length === 0 && (
              <div className="text-gray-600 text-center py-12 flex flex-col items-center gap-4 animate-pulse">
                <Activity size={32} /> Waiting for telemetry...
              </div>
            )}
          </div>
        </div>

        <div className="bg-[#0a0a0a] border border-white/5 rounded-2xl p-5 flex flex-col shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 w-[1px] h-full bg-gradient-to-b from-transparent via-purple-500/30 to-transparent"></div>
          <h3 className="font-bold tracking-widest text-xs text-gray-400 uppercase mb-4 z-10 flex items-center gap-2">
            <ShieldAlert size={14} className="text-purple-500" /> Target Firmware Array
          </h3>
          <div className="flex-1 flex items-center justify-center relative bg-black/50 rounded-xl border border-white/5 overflow-hidden">
            {/* Animated SVG Circuit representation */}
            <div className="absolute inset-0 opacity-20 animate-pulse-glow flex items-center justify-center">
              <svg viewBox="0 0 100 100" className="w-full h-full p-4" fill="none" stroke="currentColor" strokeWidth="0.5">
                <circle cx="50" cy="50" r="30" stroke="#8b5cf6" />
                <circle cx="50" cy="50" r="40" stroke="#3b82f6" strokeDasharray="4 4" className="animate-spin-slow" />
                <circle cx="50" cy="50" r="20" stroke="#10b981" />
                <line x1="50" y1="20" x2="50" y2="0" stroke="#8b5cf6" />
                <line x1="50" y1="100" x2="50" y2="80" stroke="#8b5cf6" />
                <line x1="20" y1="50" x2="0" y2="50" stroke="#3b82f6" />
                <line x1="100" y1="50" x2="80" y2="50" stroke="#3b82f6" />
                <circle cx="50" cy="50" r="4" fill="#ef4444" className="animate-ping" />
              </svg>
            </div>
            <div className="z-10 text-center">
              <p className="text-white font-mono text-2xl font-black tracking-tight">{metrics.risks}</p>
              <p className="text-gray-500 text-xs uppercase tracking-widest mt-1">Identified Nodes</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon: Icon, color = 'text-white', glow = '' }: any) {
  return (
    <div className={`bg-[#0a0a0a] border border-white/5 rounded-2xl p-6 flex items-center justify-between relative overflow-hidden group hover:border-white/20 transition-all ${glow}`}>
      <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
      <div className="z-10">
        <p className="text-gray-500 text-xs font-bold tracking-widest uppercase mb-2">{title}</p>
        <p className={`text-4xl font-black font-mono tracking-tighter ${color}`}>{value}</p>
      </div>
      <div className={`p-4 rounded-xl bg-black border border-white/5 z-10 shadow-lg ${color}`}>
        <Icon size={24} />
      </div>
    </div>
  );
}
