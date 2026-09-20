import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Overview from './components/Overview';

import { motion } from 'framer-motion';
import DeepDive from './components/DeepDive';
import TestLab from './components/TestLab';
import BehaviorGraph from './components/BehaviorGraph';
import Failures from './components/Failures';

function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<any>(null);

  useEffect(() => {
    // Start a new run on mount
    fetch('/api/runs', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        if (data.id) {
          setRunId(data.id);
        }
      })
      .catch((err) => console.error('Failed to start run', err));
  }, []);

  useEffect(() => {
    if (!runId) return;
    
    // Poll run status every 2 seconds
    const interval = setInterval(() => {
      fetch(`/api/runs/${runId}`)
        .then(res => res.json())
        .then(data => setRunStatus(data))
        .catch(err => console.error(err));
    }, 2000);

    return () => clearInterval(interval);
  }, [runId]);

  const renderContent = () => {
    switch (activeTab) {
      case 'Overview':
        return <Overview runId={runId} />;
      case 'Test Lab':
        return <TestLab runId={runId} />;
      case 'Deep Dive (Code)':
        return <DeepDive runId={runId} />;
      case 'Behavior Graph':
        return <BehaviorGraph runId={runId} />;
      case 'Failures':
        return <Failures runId={runId} />;
      case 'Regressions':
        return <div className="p-6">Regressions Panel (Coming Soon)</div>;
      case 'Simulators':
        return <div className="p-6">Simulators Panel (Coming Soon)</div>;
      default:
        return <Overview runId={runId} />;
    }
  };

  return (
    <div className="flex h-screen bg-agent-900 text-white font-sans overflow-hidden">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} runStatus={runStatus} />
      <main className="flex-1 overflow-auto bg-[#0a0a0a]">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
        >
          {renderContent()}
        </motion.div>
      </main>
    </div>
  );
}

export default App;
