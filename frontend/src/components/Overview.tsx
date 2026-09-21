import { useState, useEffect } from 'react';
import { Activity, ShieldAlert, CheckCircle, XCircle, Zap, FileText, Clock, Cpu } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Overview({ runId }: { runId: string | null }) {
  const [events, setEvents] = useState<any[]>([]);
  const [tests, setTests] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({ total: 0, passed: 0, failed: 0, risks: 0 });
  const [runStatus, setRunStatus] = useState<string>('running');

  useEffect(() => {
    if (!runId) return;

    const fetchData = () => {
      fetch(`/api/runs/${runId}/tests`)
        .then(res => res.json())
        .then(data => {
          if (data.tests && Array.isArray(data.tests)) {
            const passed = data.tests.filter((t: any) => t.status === 'PASS').length;
            const failed = data.tests.filter((t: any) => t.status === 'FAIL').length;
            setMetrics(m => ({ ...m, total: data.tests.length, passed, failed }));
            setTests(data.tests);
          }
        }).catch(console.error);

      fetch(`/api/runs/${runId}/risks`)
        .then(res => res.json())
        .then(data => {
          if (data.risks && Array.isArray(data.risks)) {
            setMetrics(m => ({ ...m, risks: data.risks.length }));
          }
        }).catch(console.error);

      fetch(`/api/runs/${runId}`)
        .then(res => res.json())
        .then(data => {
          if (data.status) setRunStatus(data.status);
        }).catch(console.error);

      fetch(`/api/runs/${runId}/events`)
        .then(res => res.json())
        .then(data => {
          if (data.events && Array.isArray(data.events)) {
            setEvents(data.events.slice(0, 50).reverse());
          }
        }).catch(console.error);
    };

    fetchData();
    const interval = setInterval(fetchData, 1500);

    return () => {
      clearInterval(interval);
    };
  }, [runId]);

  const isRunning = runStatus === 'running' || runStatus === 'starting';

  return (
    <div className="p-6 h-full flex flex-col gap-5 bg-[#050505]">
      {/* Header */}
      <header className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">Control Console</h2>
          <div className="flex items-center gap-3 mt-1">
            <p className="text-gray-500 text-xs uppercase tracking-widest font-mono">Live Telemetry</p>
            {isRunning && (
              <div className="flex items-center gap-1.5 px-2 py-0.5 bg-blue-950/50 rounded-full border border-blue-500/20">
                <div className="w-2 h-2 border-[1.5px] border-blue-400 border-t-transparent rounded-full animate-spin" />
                <span className="text-blue-400 text-[9px] uppercase font-semibold tracking-wider">Simulating</span>
              </div>
            )}
            {!isRunning && runStatus === 'completed' && (
              <div className="flex items-center gap-1.5 px-2 py-0.5 bg-green-950/50 rounded-full border border-green-500/20">
                <CheckCircle size={10} className="text-green-400" />
                <span className="text-green-400 text-[9px] uppercase font-semibold tracking-wider">Complete</span>
              </div>
            )}
          </div>
        </div>
        <div className="flex gap-3">
          <a href={`/api/runs/${runId}/report`} target="_blank" rel="noreferrer" className="flex items-center gap-2 px-4 py-1.5 bg-white/5 border border-white/10 rounded-lg text-gray-400 text-xs font-medium hover:bg-white/10 transition-colors">
            <FileText size={13} />
            Report
          </a>
        </div>
      </header>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Tests Run" value={metrics.total} icon={Activity} />
        <MetricCard title="Passed" value={metrics.passed} icon={CheckCircle} color="text-emerald-400" accent="border-emerald-500/20" />
        <MetricCard title="Failed" value={metrics.failed} icon={XCircle} color="text-red-400" accent="border-red-500/20" />
        <MetricCard title="Risks" value={metrics.risks} icon={ShieldAlert} color="text-amber-400" accent="border-amber-500/20" />
      </div>

      {/* Main Content Grid */}
      <div className="flex-1 grid grid-cols-5 gap-4 min-h-0">
        {/* Activity Stream */}
        <div className="col-span-3 bg-[#0a0a0a] border border-white/5 rounded-xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
            <h3 className="font-semibold tracking-wide text-xs text-gray-400 uppercase flex items-center gap-2">
              <Zap size={12} className="text-blue-400" /> Activity Stream
            </h3>
            <span className="text-[10px] text-gray-600 font-mono">{events.length} events</span>
          </div>
          <div className="flex-1 overflow-auto p-3 space-y-1.5 font-mono text-xs scrollbar-custom">
            <AnimatePresence initial={false}>
              {events.map((ev, i) => (
                <motion.div
                  key={`${ev.timestamp}-${i}`}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  transition={{ duration: 0.2 }}
                >
                  <div className="flex gap-3 px-3 py-2 rounded-lg hover:bg-white/[0.02] transition-colors group">
                    <span className="text-gray-700 whitespace-nowrap text-[10px] pt-0.5">{new Date(ev.timestamp || Date.now()).toLocaleTimeString()}</span>
                    <span className={`font-bold w-24 truncate text-[10px] pt-0.5 ${
                      ev.agent === 'VERIFIER' ? 'text-emerald-500' :
                      ev.agent === 'EXECUTOR' ? 'text-blue-400' :
                      ev.agent === 'PLANNER' ? 'text-purple-400' :
                      ev.agent === 'DIAGNOSER' ? 'text-red-400' :
                      'text-gray-500'
                    }`}>[{ev.agent || 'SYSTEM'}]</span>
                    <span className="text-gray-400 flex-1 leading-relaxed">{ev.reason || ev.message || JSON.stringify(ev)}</span>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
            {events.length === 0 && (
              <div className="text-gray-600 text-center py-16 flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-gray-700 border-t-blue-500 rounded-full animate-spin" />
                <span className="text-[10px] uppercase tracking-widest">Awaiting telemetry...</span>
              </div>
            )}
          </div>
        </div>

        {/* Live Test Progress */}
        <div className="col-span-2 bg-[#0a0a0a] border border-white/5 rounded-xl flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-white/5 flex items-center justify-between">
            <h3 className="font-semibold tracking-wide text-xs text-gray-400 uppercase flex items-center gap-2">
              <Cpu size={12} className="text-purple-400" /> Test Progress
            </h3>
            <span className="text-[10px] text-gray-600 font-mono">{metrics.passed + metrics.failed}/{metrics.total}</span>
          </div>
          <div className="flex-1 overflow-auto p-3 space-y-1 scrollbar-custom">
            <AnimatePresence initial={false}>
              {tests.map((test: any, i: number) => (
                <motion.div
                  key={test.test_id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: i * 0.03 }}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg hover:bg-white/[0.02] transition-colors"
                >
                  <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                    test.status === 'PASS' ? 'bg-emerald-400' :
                    test.status === 'FAIL' ? 'bg-red-400' :
                    'bg-yellow-400'
                  }`} />
                  <span className="text-gray-500 text-[10px] font-mono w-20 truncate">{test.test_id}</span>
                  <span className="text-gray-400 text-[10px] flex-1 truncate">{test.category}</span>
                  <span className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                    test.status === 'PASS' ? 'text-emerald-400 bg-emerald-950/50' :
                    test.status === 'FAIL' ? 'text-red-400 bg-red-950/50' :
                    'text-yellow-400 bg-yellow-950/50'
                  }`}>{test.status}</span>
                </motion.div>
              ))}
            </AnimatePresence>
            {tests.length === 0 && (
              <div className="text-gray-600 text-center py-16 flex flex-col items-center gap-3">
                <Clock size={20} className="text-gray-700" />
                <span className="text-[10px] uppercase tracking-widest">Generating scenarios...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon: Icon, color = 'text-white', accent = 'border-white/5' }: any) {
  return (
    <div className={`bg-[#0a0a0a] border ${accent} rounded-xl p-4 flex items-center justify-between group hover:bg-[#0d0d0d] transition-colors`}>
      <div>
        <p className="text-gray-600 text-[10px] font-semibold tracking-widest uppercase mb-1">{title}</p>
        <p className={`text-2xl font-bold font-mono tracking-tight ${color}`}>{value}</p>
      </div>
      <div className={`p-2.5 rounded-lg bg-black/50 border border-white/5 ${color}`}>
        <Icon size={16} />
      </div>
    </div>
  );
}
