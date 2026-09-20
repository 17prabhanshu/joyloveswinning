import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Overview from './components/Overview';

import { motion, AnimatePresence } from 'framer-motion';
import DeepDive from './components/DeepDive';
import TestLab from './components/TestLab';
import BehaviorGraph from './components/BehaviorGraph';
import Failures from './components/Failures';
import SetupScreen from './components/SetupScreen';

function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<any>(null);

  const handleStartRun = () => {
    // In a real implementation, we would POST the files/code here.
    // For the hackathon, we just start the demo run API.
    fetch('/api/runs', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        if (data.id) {
          setRunId(data.id);
        }
      })
      .catch((err) => console.error('Failed to start run', err));
  };

  useEffect(() => {
    if (!runId) return;
    
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
      case 'Overview': return <Overview runId={runId} />;
      case 'Test Lab': return <TestLab runId={runId} />;
      case 'Deep Dive (Code)': return <DeepDive runId={runId} />;
      case 'Behavior Graph': return <BehaviorGraph runId={runId} />;
      case 'Failures': return <Failures runId={runId} />;
      case 'Regressions': return <div className="p-6 text-gray-400">Regressions Panel (Coming Soon)</div>;
      case 'Simulators': return <div className="p-6 text-gray-400">Simulators Panel (Coming Soon)</div>;
      default: return <Overview runId={runId} />;
    }
  };

  return (
    <AnimatePresence mode="wait">
      {!runId ? (
        <motion.div key="setup" exit={{ opacity: 0, scale: 0.95 }} transition={{ duration: 0.4 }}>
          <SetupScreen onStart={handleStartRun} />
        </motion.div>
      ) : (
        <motion.div 
          key="dashboard"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8 }}
          className="flex h-screen bg-[#0a0a0a] text-white font-sans overflow-hidden"
        >
          <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} runStatus={runStatus} />
          <main className="flex-1 overflow-auto bg-[#050505] relative shadow-[-10px_0_30px_rgba(0,0,0,0.5)]">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="h-full"
              >
                {renderContent()}
              </motion.div>
            </AnimatePresence>
          </main>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default App;
