import { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { Terminal, Code, Cpu, Bot } from 'lucide-react';
import { motion } from 'framer-motion';

const renderMessage = (text: string) => {
  let cleanText = text.startsWith('[Agent]') ? text.substring(7).trim() : text;
  cleanText = cleanText.startsWith('[Gemini Agent]') ? cleanText.substring(14).trim() : cleanText;

  return cleanText.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} className="h-2"></div>;
    
    const parts = line.split(/(\*\*.*?\*\*|`.*?`)/g);
    return (
      <p key={i} className="mb-1.5 leading-relaxed">
        {parts.map((part, j) => {
          if (part.startsWith('**') && part.endsWith('**')) {
            return <strong key={j} className="text-white font-semibold">{part.slice(2, -2)}</strong>;
          }
          if (part.startsWith('`') && part.endsWith('`')) {
            return <code key={j} className="bg-black/30 border border-white/10 text-cyan-400 px-1.5 py-0.5 rounded font-mono text-xs">{part.slice(1, -1)}</code>;
          }
          // Process *italic* if needed, but we'll stick to bold for now
          return <span key={j}>{part}</span>;
        })}
      </p>
    );
  });
};

export default function DeepDive({ runId }: { runId: string | null }) {
  const [files, setFiles] = useState<Record<string, string>>({});
  const [activeFile, setActiveFile] = useState<string>('');
  const [chatLog, setChatLog] = useState<{ role: 'user' | 'agent', content: string }[]>([
    { role: 'agent', content: 'Agent connected. Ask me anything about the firmware logic, vulnerabilities, or my test decisions.' }
  ]);
  const [input, setInput] = useState('');

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;
    
    const fetchFirmware = () => {
      fetch(`/api/firmware/${runId}`)
        .then(res => res.json())
        .then(data => {
          if (cancelled) return;
          if (data.files) {
            setFiles(data.files);
            const first = Object.keys(data.files)[0];
            if (first) setActiveFile(first);
            if (interval) clearInterval(interval);
          }
        })
        .catch(console.error);
    };

    fetchFirmware();
    const interval = setInterval(fetchFirmware, 3000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [runId]);

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !runId) return;

    const userMsg = input;
    setChatLog(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');

    try {
      const res = await fetch(`/api/runs/${runId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMsg })
      });
      const data = await res.json();
      
      setChatLog(prev => [...prev, { 
        role: 'agent', 
        content: data.response || "I am currently analyzing the AST structure..." 
      }]);
    } catch (err) {
      setChatLog(prev => [...prev, { role: 'agent', content: "Connection to agent brain lost." }]);
    }
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
        className="w-[550px] flex flex-col gap-4"
      >
        <div className="flex-1 bg-agent-800 border border-agent-700 rounded-lg flex flex-col overflow-hidden">
          <div className="p-3 border-b border-agent-700 bg-agent-900 flex items-center gap-2">
            <Cpu size={16} className="text-agent-accent" />
            <span className="font-semibold text-sm">Agent "Grill Me" Chat</span>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto space-y-4 scrollbar-custom">
            {chatLog.map((msg, i) => (
              <motion.div 
                initial={{ opacity: 0, y: 10, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                key={i} 
                className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
              >
                <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center border shadow-sm overflow-hidden ${
                  msg.role === 'user' 
                    ? 'bg-blue-600/20 border-blue-500/50' 
                    : 'bg-cyan-900/30 border-cyan-500/50 text-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.2)]'
                }`}>
                  {msg.role === 'user' ? (
                    <img src="https://api.dicebear.com/7.x/cats/svg?seed=Meow&backgroundColor=transparent" alt="User Cat" className="w-full h-full object-cover" />
                  ) : (
                    <Bot size={16} />
                  )}
                </div>
                
                <div className={`max-w-[75%] rounded-2xl p-4 text-sm shadow-md ${
                  msg.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-none' 
                    : 'bg-[#111111] border border-white/10 text-gray-300 rounded-tl-none font-sans'
                }`}>
                  {msg.role === 'user' ? msg.content : renderMessage(msg.content)}
                </div>
              </motion.div>
            ))}
          </div>

          <form onSubmit={handleChat} className="p-4 border-t border-agent-700 bg-agent-900 shadow-[0_-10px_20px_rgba(0,0,0,0.3)] relative z-10">
            <div className="flex gap-3">
              <input 
                type="text" 
                value={input}
                onChange={e => setInput(e.target.value)}
                placeholder="Ask agent to explain a vulnerability or suggest a fix..."
                className="flex-1 bg-agent-800 border border-agent-700 rounded-lg px-4 py-3 text-sm focus:outline-none focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/30 text-white placeholder-gray-500 transition-all shadow-inner"
              />
              <button 
                type="submit" 
                className="bg-blue-600 text-white px-6 py-3 rounded-lg font-bold tracking-widest text-xs uppercase hover:bg-blue-500 hover:shadow-[0_0_15px_rgba(37,99,235,0.4)] transition-all flex items-center justify-center min-w-[80px]"
              >
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
