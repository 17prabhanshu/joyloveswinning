import { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Terminal, Code, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

export default function DeepDive({ runId }: { runId: string | null }) {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeFile, setActiveFile] = useState<string>('');
  const [chatLog, setChatLog] = useState<{ role: 'user' | 'agent', content: string }[]>([
    { role: 'agent', content: 'Agent connected. Ask me anything about the firmware logic, vulnerabilities, or my test decisions.' }
  ]);
  const [input, setInput] = useState('');

  useEffect(() => {
    if (!runId) return;
    fetch(`/api/firmware/${runId}`)
      .then(res => res.json())
      .then(data => {
        if (data.files) {
          setFiles(data.files);
          const first = Object.keys(data.files)[0];
          if (first) setActiveFile(first);
        }
      })
      .catch(console.error);
  }, [runId]);

  const handleChat = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setChatLog(prev => [...prev, { role: 'user', content: input }]);
    setInput('');

    // Mock LLM response for instant feedback
    setTimeout(() => {
      setChatLog(prev => [...prev, { 
        role: 'agent', 
        content: `Analyzing ${activeFile}... I see that the fan controller logic lacks a debounce delay on the GPIO write. This is risky because rapid state transitions on inductive loads can cause back-EMF spikes.` 
      }]);
    }, 1000);
  };

  return (
    <div className="h-full flex gap-4 p-6 text-white bg-[#0a0a0a]">
      {/* Code Editor Pane */}
      <motion.div 
        initial={{ opacity: 0, x: -20 }}
        animate={{ opacity: 1, x: 0 }}
        className="flex-1 flex flex-col bg-agent-800 border border-agent-700 rounded-lg overflow-hidden shadow-2xl shadow-agent-900/50"
      >
        <div className="flex bg-agent-900 border-b border-agent-700">
          {Object.keys(files).map(fileName => (
            <button
              key={fileName}
              onClick={() => setActiveFile(fileName)}
              className={`px-4 py-2 font-mono text-sm border-r border-agent-700 flex items-center gap-2 transition-colors
                ${activeFile === fileName ? 'bg-agent-800 text-agent-accent border-t-2 border-t-agent-accent' : 'text-gray-400 hover:bg-agent-800 hover:text-white'}`}
            >
              <Code size={14} />
              {fileName}
            </button>
          ))}
        </div>
        <div className="flex-1 relative">
          <Editor
            height="100%"
            language="c"
            theme="vs-dark"
            value={files[activeFile] || '// Loading firmware source...'}
            options={{
              readOnly: true,
              minimap: { enabled: true },
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 14,
              scrollBeyondLastLine: false,
            }}
          />
        </div>
      </motion.div>

      {/* Agent Chat / Terminal Pane */}
      <motion.div 
        initial={{ opacity: 0, x: 20 }}
        animate={{ opacity: 1, x: 0 }}
        className="w-[400px] flex flex-col gap-4"
      >
        <div className="flex-1 bg-agent-800 border border-agent-700 rounded-lg flex flex-col overflow-hidden">
          <div className="p-3 border-b border-agent-700 bg-agent-900 flex items-center gap-2">
            <Cpu size={16} className="text-agent-accent" />
            <span className="font-semibold text-sm">Agent "Grill Me" Chat</span>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto space-y-4 scrollbar-custom">
            {chatLog.map((msg, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                key={i} 
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-[85%] rounded-lg p-3 text-sm ${
                  msg.role === 'user' 
                    ? 'bg-agent-accent text-white rounded-br-none' 
                    : 'bg-agent-900 border border-agent-700 text-gray-300 rounded-bl-none font-mono'
                }`}>
                  {msg.content}
                </div>
              </motion.div>
            ))}
          </div>

          <form onSubmit={handleChat} className="p-3 border-t border-agent-700 bg-agent-900">
            <div className="flex gap-2">
              <input 
                type="text" 
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask agent to explain..."
                className="flex-1 bg-agent-800 border border-agent-700 rounded px-3 py-2 text-sm focus:outline-none focus:border-agent-accent text-white"
              />
              <button type="submit" className="bg-agent-accent text-white px-3 py-2 rounded font-medium hover:bg-blue-600 transition-colors">
                Ask
              </button>
            </div>
          </form>
        </div>

        <div className="h-1/3 bg-black border border-agent-700 rounded-lg flex flex-col overflow-hidden font-mono">
          <div className="px-3 py-1 bg-agent-900 border-b border-agent-700 text-xs text-gray-400 flex items-center gap-2">
            <Terminal size={12} /> Live Trace
          </div>
          <div className="p-3 text-xs text-green-500 overflow-y-auto space-y-1">
            <p className="animate-pulse">_ await connection...</p>
            <p>&gt; initializing semantic AST search</p>
            <p>&gt; extracting control flow graph</p>
            <p>&gt; identifying target boundary constants</p>
            <p>&gt; analyzing MMIO definitions in st_prep_buffer()</p>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
