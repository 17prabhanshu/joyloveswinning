import { useState, useEffect } from 'react';

export default function TestLab({ runId }: { runId: string | null }) {
  const [tests, setTests] = useState<any[]>([]);

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

  return (
    <div className="p-8 h-full flex flex-col gap-6 bg-[#050505]">
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
                <tr key={test.test_id} className="hover:bg-blue-900/10 transition-colors group cursor-pointer">
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
    </div>
  );
}
