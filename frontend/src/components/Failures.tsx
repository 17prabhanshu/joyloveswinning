import { useState, useEffect } from 'react';
import { AlertTriangle, MapPin, Search } from 'lucide-react';

export default function Failures({ runId }: { runId: string | null }) {
  const [failures, setFailures] = useState<any[]>([]);

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/runs/${runId}/failures`)
      .then(res => res.json())
      .then(data => {
        if (data.failures && Array.isArray(data.failures)) {
          setFailures(data.failures);
        }
      })
      .catch(console.error);
  }, [runId]);

  return (
    <div className="p-6 h-full overflow-auto scrollbar-custom">
      <header className="mb-6">
        <h2 className="text-2xl font-bold text-agent-alert flex items-center gap-2">
          <AlertTriangle />
          Triaged Failures
        </h2>
        <p className="text-gray-400 text-sm mt-1">Divergences between expected and observed behavior</p>
      </header>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {failures.map((f, i) => (
          <div key={i} className="bg-agent-800 border border-agent-alert/50 rounded-lg p-5 flex flex-col gap-4 relative overflow-hidden group">
            <div className="absolute top-0 left-0 w-1 h-full bg-agent-alert"></div>
            
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-bold text-lg font-mono text-white">{f.id || `FAILURE-${i+1}`}</h3>
                <div className="flex items-center gap-2 text-sm text-gray-400 mt-1">
                  <MapPin size={14} />
                  <span className="font-mono">{f.source_location || 'Unknown location'}</span>
                </div>
              </div>
              <div className="px-3 py-1 bg-agent-900 border border-agent-700 rounded text-xs font-bold text-agent-warning flex items-center gap-1">
                <Search size={12} />
                CONFIDENCE: {f.confidence || 'HIGH'}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 bg-agent-900 p-4 rounded border border-agent-700">
              <div>
                <p className="text-xs text-gray-500 font-bold mb-1 uppercase">Expected</p>
                <p className="font-mono text-sm text-agent-accent whitespace-pre-wrap">{f.expected || 'N/A'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 font-bold mb-1 uppercase">Observed</p>
                <p className="font-mono text-sm text-agent-alert whitespace-pre-wrap">{f.observed || 'N/A'}</p>
              </div>
            </div>

            <div className="bg-agent-700/30 p-4 rounded">
              <p className="text-xs text-gray-400 font-bold mb-2 uppercase">Root Cause Hypothesis</p>
              <p className="text-sm text-gray-200 leading-relaxed">{f.cause_hypothesis || 'No hypothesis generated.'}</p>
            </div>

            <div className="flex gap-4 text-xs font-mono text-gray-500 mt-2">
              <span>Minimization: {f.minimization_stats || 'Done'}</span>
              <span>Regression ID: {f.regression_id || 'None'}</span>
            </div>
          </div>
        ))}

        {failures.length === 0 && (
          <div className="col-span-full p-12 flex flex-col items-center justify-center text-gray-500 border-2 border-dashed border-agent-700 rounded-lg">
            <CheckCircle className="mb-4 opacity-50" size={48} />
            <p className="text-lg">No failures detected in current run</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { CheckCircle } from 'lucide-react';
