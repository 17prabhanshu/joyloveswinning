import { Activity, Beaker, GitGraph, AlertTriangle, GitMerge, Cpu, TerminalSquare, Sun, Moon } from 'lucide-react';
import { useState } from 'react';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  runStatus: any;
  onNewSession?: () => void;
}

const TABS = [
  { name: 'Overview', icon: Activity },
  { name: 'Test Lab', icon: Beaker },
  { name: 'AI Copilot', icon: TerminalSquare },
  { name: 'Behavior Graph', icon: GitGraph },
  { name: 'Failures', icon: AlertTriangle },
  { name: 'Regressions', icon: GitMerge },
  { name: 'Simulators', icon: Cpu },
];

export default function Sidebar({ activeTab, setActiveTab, runStatus, onNewSession }: SidebarProps) {
  const [theme, setTheme] = useState('dark');

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <aside className="w-64 bg-agent-800 border-r border-agent-700 flex flex-col h-full shadow-2xl relative z-20">
      <div className="p-6 border-b border-agent-700">
        <h1 className="text-xl font-bold tracking-wider text-white flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-agent-accent glow-accent animate-pulse"></span>
          JOY
        </h1>
        <p className="text-xs text-gray-400 mt-2 font-mono uppercase tracking-widest">Autonomous Red-Team</p>
      </div>

      <nav className="flex-1 p-4 space-y-1">
        {TABS.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.name;
          return (
            <button
              key={tab.name}
              onClick={() => setActiveTab(tab.name)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 ${
                isActive 
                  ? 'bg-agent-700 text-white shadow-md' 
                  : 'text-gray-400 hover:bg-agent-700/50 hover:text-gray-200'
              }`}
            >
              <Icon size={18} className={isActive ? 'text-agent-accent' : ''} />
              <span className="font-medium text-sm">{tab.name}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-agent-700 space-y-4">
        {onNewSession && (
          <button 
            onClick={onNewSession}
            className="w-full flex items-center justify-center py-2 rounded bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm tracking-wide transition-all shadow-lg"
          >
            + NEW FIRMWARE
          </button>
        )}
        <div className="bg-agent-900 rounded-md p-4 flex flex-col gap-2 border border-agent-700/50">
          <span className="text-xs text-gray-500 font-mono uppercase">System Status</span>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${runStatus?.status === 'running' ? 'bg-agent-accent glow-accent animate-pulse' : 'bg-gray-500'}`}></div>
            <span className="text-sm font-medium capitalize">{runStatus?.status || 'Idle'}</span>
          </div>
        </div>
        
        <button 
          onClick={toggleTheme}
          className="w-full flex items-center justify-center gap-2 py-2 rounded border border-agent-700/50 text-gray-400 hover:text-white hover:bg-agent-700 transition-colors"
        >
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
          <span className="text-xs font-mono uppercase">{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
      </div>
    </aside>
  );
}
