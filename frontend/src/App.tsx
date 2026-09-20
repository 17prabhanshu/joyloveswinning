import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import Overview from './components/Overview';

import { motion, AnimatePresence } from 'framer-motion';
import DeepDive from './components/DeepDive';
import TestLab from './components/TestLab';
import BehaviorGraph from './components/BehaviorGraph';
import Failures from './components/Failures';
import Simulators from './components/Simulators';
import Regressions from './components/Regressions';
import SetupScreen from './components/SetupScreen';

function App() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<any>(null);

  const handleStartRun = (_files: File[], code: string, _resc: File | null) => {
    // In a real implementation, we would POST the files/code here.
    // For the hackathon, we just start the demo run API.
    fetch('/api/runs', { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code: code })
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.run_id) {
          setRunId(data.run_id);
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
      case 'Regressions': return <Regressions runId={runId} />;
      case 'Simulators': return <Simulators runId={runId} />;
      default: return <Overview runId={runId} />;
    }
  };

const FloatingParticles = () => {
  return (
    <div className="absolute inset-0 pointer-events-none overflow-hidden opacity-30 z-0">
      {[...Array(20)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full bg-cyan-500/20 blur-md"
          style={{
            width: Math.random() * 100 + 50 + 'px',
            height: Math.random() * 100 + 50 + 'px',
            left: Math.random() * 100 + '%',
            top: Math.random() * 100 + '%',
          }}
          animate={{
            x: [Math.random() * 100 - 50, Math.random() * 100 - 50, Math.random() * 100 - 50],
            y: [Math.random() * 100 - 50, Math.random() * 100 - 50, Math.random() * 100 - 50],
            scale: [1, 1.2, 1],
          }}
          transition={{
            duration: Math.random() * 10 + 15,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      ))}
    </div>
  );
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
          <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} runStatus={runStatus} onNewSession={() => setRunId(null)} />
          <main className="flex-1 overflow-auto bg-[#050505] relative shadow-[-10px_0_30px_rgba(0,0,0,0.5)] border-l border-white/5">
            <FloatingParticles />
            {/* Ambient Background Glows */}
            <div className="absolute top-[-20%] right-[-10%] w-[50%] h-[50%] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none z-0"></div>
            <div className="absolute bottom-[-20%] left-[-10%] w-[50%] h-[50%] bg-purple-500/10 blur-[120px] rounded-full pointer-events-none z-0"></div>
            
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 20, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -20, scale: 0.98 }}
                transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
                className="h-full relative z-10"
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
