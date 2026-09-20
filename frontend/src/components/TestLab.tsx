import { useState, useEffect } from 'react';

export default function TestLab({ runId }: { runId: string | null }) {
  const [tests, setTests] = useState<any[]>([]);

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/runs/${runId}/tests`)
      .then(res => res.json())
      .then(data => {
        if (Array.isArray(data)) setTests(data);
      })
      .catch(console.error);
  }, [runId]);

  return (
    <div className="p-6 h-full flex flex-col gap-4">
      <header>
        <h2 className="text-2xl font-bold">Test Lab</h2>
        <p className="text-gray-400 text-sm mt-1">Autonomous test generation and execution results</p>
      </header>

      <div className="flex-1 bg-agent-800 border border-agent-700 rounded-lg overflow-hidden flex flex-col">
        <div className="overflow-x-auto flex-1 scrollbar-custom">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-agent-900/80 sticky top-0 border-b border-agent-700">
              <tr>
                <th className="p-4 font-medium text-gray-400">ID</th>
                <th className="p-4 font-medium text-gray-400">Status</th>
                <th className="p-4 font-medium text-gray-400">Target</th>
                <th className="p-4 font-medium text-gray-400">Category</th>
                <th className="p-4 font-medium text-gray-400 w-1/3">Why</th>
                <th className="p-4 font-medium text-gray-400">Expected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-agent-700">
              {tests.map((test, i) => (
                <tr key={i} className="hover:bg-agent-700/30 transition-colors">
                  <td className="p-4 font-mono text-gray-300">{test.id || `T-${i}`}</td>
                  <td className="p-4">
                    <span className={`px-2 py-1 rounded text-xs font-bold ${
                      test.status === 'PASS' ? 'bg-agent-accent/20 text-agent-accent border border-agent-accent/30' :
                      test.status === 'FAIL' ? 'bg-agent-alert/20 text-agent-alert border border-agent-alert/30' :
                      'bg-agent-warning/20 text-agent-warning border border-agent-warning/30'
                    }`}>
                      {test.status || 'PENDING'}
                    </span>
                  </td>
                  <td className="p-4 font-mono text-blue-400">{test.target}</td>
                  <td className="p-4 text-gray-300">{test.category}</td>
                  <td className="p-4 text-gray-400 truncate max-w-xs" title={test.why}>{test.why}</td>
                  <td className="p-4 text-gray-400 truncate max-w-xs" title={test.expected}>{test.expected}</td>
                </tr>
              ))}
              {tests.length === 0 && (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-500">No tests available yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
