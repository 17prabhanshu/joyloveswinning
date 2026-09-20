import { useState, useEffect } from 'react';
import { Activity, ShieldAlert, CheckCircle, XCircle } from 'lucide-react';

export default function Overview({ runId }: { runId: string | null }) {
  const [events, setEvents] = useState<any[]>([]);
  const [metrics, setMetrics] = useState({ total: 0, passed: 0, failed: 0, risks: 0 });

  useEffect(() => {
    if (!runId) return;

    // Fetch tests to aggregate metrics
    fetch(`/api/runs/${runId}/tests`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          const passed = data.filter(t => t.status === 'PASS').length;
          const failed = data.filter(t => t.status === 'FAIL').length;
          setMetrics(m => ({ ...m, total: data.length, passed, failed }));
        }
      }).catch(console.error);

    fetch(`/api/runs/${runId}/risks`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) {
          setMetrics(m => ({ ...m, risks: data.length }));
        }
      }).catch(console.error);

    // Setup SSE for events
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
    <div className="p-6 h-full flex flex-col gap-6">
      <header>
        <h2 className="text-2xl font-bold">Control Console</h2>
        <p className="text-gray-400 text-sm mt-1">Real-time telemetry and analysis overview</p>
      </header>

      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Total Tests" value={metrics.total} icon={Activity} />
        <MetricCard title="Passed" value={metrics.passed} icon={CheckCircle} color="text-agent-accent" />
        <MetricCard title="Failed" value={metrics.failed} icon={XCircle} color="text-agent-alert" />
        <MetricCard title="Risks Identified" value={metrics.risks} icon={ShieldAlert} color="text-agent-warning" />
      </div>

      <div className="flex-1 grid grid-cols-3 gap-6 min-h-0">
        <div className="col-span-2 bg-agent-800 border border-agent-700 rounded-lg flex flex-col overflow-hidden">
          <div className="p-4 border-b border-agent-700 bg-agent-800/50">
            <h3 className="font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-agent-accent animate-pulse"></span>
              Live Activity Stream
            </h3>
          </div>
          <div className="flex-1 overflow-auto p-4 space-y-3 font-mono text-sm scrollbar-custom">
            {events.map((ev, i) => (
              <div key={i} className="flex gap-4 p-3 bg-agent-900/50 rounded border border-agent-700/30 hover:border-agent-700 transition-colors">
                <span className="text-gray-500 whitespace-nowrap">{new Date(ev.timestamp || Date.now()).toLocaleTimeString()}</span>
                <span className="text-blue-400 font-bold w-24 truncate">[{ev.agent || 'SYSTEM'}]</span>
                <span className="text-gray-200 flex-1">{ev.reason || ev.message || JSON.stringify(ev)}</span>
              </div>
            ))}
            {events.length === 0 && (
              <div className="text-gray-500 text-center py-8">Waiting for telemetry...</div>
            )}
          </div>
        </div>

        <div className="bg-agent-800 border border-agent-700 rounded-lg p-4 flex flex-col">
          <h3 className="font-semibold mb-4 text-agent-warning">Risk Map</h3>
          <div className="flex-1 flex items-center justify-center border-2 border-dashed border-agent-700 rounded bg-agent-900/30">
            <p className="text-gray-500 text-sm">Visualizer Initializing...</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, icon: Icon, color = 'text-white' }: any) {
  return (
    <div className="bg-agent-800 border border-agent-700 rounded-lg p-4 flex items-center justify-between">
      <div>
        <p className="text-gray-400 text-sm font-medium mb-1">{title}</p>
        <p className={`text-3xl font-bold font-mono ${color}`}>{value}</p>
      </div>
      <div className={`p-3 rounded-full bg-agent-900 border border-agent-700 ${color}`}>
        <Icon size={24} />
      </div>
    </div>
  );
}
