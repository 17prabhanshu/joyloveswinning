import { useState } from 'react';
import { motion } from 'framer-motion';
import { UploadCloud, Code, Cpu, ArrowRight } from 'lucide-react';

export default function SetupScreen({ onStart }: { onStart: (files: File[], code: string, resc: File | null, fastMode?: boolean) => void }) {
  const [activeTab, setActiveTab] = useState<'upload' | 'paste'>('upload');
  const [code, setCode] = useState('');
  const [rescFile, setRescFile] = useState<File | null>(null);
  const [fwFiles, setFwFiles] = useState<File[]>([]);
  const [fastMode, setFastMode] = useState(false);

  const handleStart = () => {
    onStart(fwFiles, code, rescFile, fastMode);
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white flex items-center justify-center p-6 relative overflow-hidden">
      {/* Background Graphic Effects */}
      <div className="absolute top-[-20%] left-[-10%] w-[60%] h-[60%] bg-blue-900/20 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] bg-purple-900/20 blur-[120px] rounded-full pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-4xl w-full bg-[#0a0a0a]/80 backdrop-blur-xl border border-white/10 rounded-2xl shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden z-10"
      >
        <div className="p-10 border-b border-white/5">
          <h1 className="text-4xl font-extrabold tracking-tight bg-gradient-to-br from-white to-gray-500 bg-clip-text text-transparent">
            Initialize Red-Team Agent
          </h1>
          <p className="text-gray-400 mt-3 text-lg font-light max-w-2xl">
            Upload your embedded C firmware or paste the source directly. Provide an optional Renode .resc file for cycle-accurate hardware simulation.
          </p>
        </div>

        <div className="flex bg-black/40 border-b border-white/5">
          <button 
            className={`flex-1 py-4 text-sm font-semibold tracking-wider transition-colors flex items-center justify-center gap-2 ${activeTab === 'upload' ? 'text-blue-400 border-b-2 border-blue-400 bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            onClick={() => setActiveTab('upload')}
          >
            <UploadCloud size={18} /> UPLOAD FILES
          </button>
          <button 
            className={`flex-1 py-4 text-sm font-semibold tracking-wider transition-colors flex items-center justify-center gap-2 ${activeTab === 'paste' ? 'text-blue-400 border-b-2 border-blue-400 bg-white/5' : 'text-gray-500 hover:text-gray-300'}`}
            onClick={() => setActiveTab('paste')}
          >
            <Code size={18} /> PASTE SOURCE
          </button>
        </div>

        <div className="p-10 flex flex-col gap-8">
          {activeTab === 'upload' ? (
            <div className="grid grid-cols-2 gap-6">
              {/* Firmware Upload */}
              <div className="relative group cursor-pointer">
                <div className="absolute inset-0 bg-blue-500/20 blur-xl group-hover:bg-blue-500/30 transition-all opacity-0 group-hover:opacity-100 rounded-xl" />
                <label className="relative flex flex-col items-center justify-center h-48 border-2 border-dashed border-white/10 rounded-xl hover:border-blue-500/50 bg-[#111] transition-all cursor-pointer overflow-hidden">
                  <input type="file" multiple accept=".c,.h,.cpp,.hpp" className="hidden" onChange={(e) => setFwFiles(Array.from(e.target.files || []))} />
                  <UploadCloud size={32} className="text-blue-400 mb-3" />
                  <span className="font-semibold text-gray-200">Firmware Source (.c / .h)</span>
                  <span className="text-sm text-gray-500 mt-1">{fwFiles.length > 0 ? `${fwFiles.length} files selected` : 'Drag & drop or click'}</span>
                </label>
              </div>

              {/* Renode Upload */}
              <div className="relative group cursor-pointer">
                <div className="absolute inset-0 bg-purple-500/20 blur-xl group-hover:bg-purple-500/30 transition-all opacity-0 group-hover:opacity-100 rounded-xl" />
                <label className="relative flex flex-col items-center justify-center h-48 border-2 border-dashed border-white/10 rounded-xl hover:border-purple-500/50 bg-[#111] transition-all cursor-pointer overflow-hidden">
                  <input type="file" accept=".resc" className="hidden" onChange={(e) => setRescFile(e.target.files?.[0] || null)} />
                  <Cpu size={32} className="text-purple-400 mb-3" />
                  <span className="font-semibold text-gray-200">Hardware Config (.resc)</span>
                  <span className="text-sm text-gray-500 mt-1">{rescFile ? rescFile.name : 'Optional Renode Board Config'}</span>
                </label>
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-4">
              <textarea 
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="// Paste your C firmware code here...&#10;void control_fan(float temp) { ... }"
                className="w-full h-64 bg-[#111] border border-white/10 rounded-xl p-4 font-mono text-sm text-gray-300 focus:outline-none focus:border-blue-500/50 resize-none"
              />
              <div className="relative group cursor-pointer w-1/2">
                <label className="relative flex items-center justify-between p-4 border border-white/10 rounded-xl hover:border-purple-500/50 bg-[#111] transition-all cursor-pointer">
                  <div className="flex items-center gap-3">
                    <Cpu size={20} className="text-purple-400" />
                    <div>
                      <span className="block font-semibold text-gray-200 text-sm">Attach .resc (Optional)</span>
                      <span className="block text-xs text-gray-500">{rescFile ? rescFile.name : 'No file selected'}</span>
                    </div>
                  </div>
                  <input type="file" accept=".resc" className="hidden" onChange={(e) => setRescFile(e.target.files?.[0] || null)} />
                </label>
              </div>
            </div>
          )}

          <div className="flex justify-end pt-4 border-t border-white/5">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setFastMode(!fastMode)}
                className={`w-2 h-2 rounded-full transition-colors ${fastMode ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-white/10 hover:bg-white/30'}`}
                title="Toggle Deterministic Mock Mode"
              />
              <button 
                onClick={handleStart}
                disabled={fwFiles.length === 0 && code.trim() === ''}
                className="relative overflow-hidden group px-8 py-3 rounded-lg font-bold tracking-wide text-white disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 transition-all flex items-center gap-2"
              >
              <div className="absolute inset-0 w-full h-full bg-gradient-to-r from-transparent via-white/20 to-transparent translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              BEGIN ANALYSIS <ArrowRight size={18} className="group-hover:translate-x-1 transition-transform" />
            </button>
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
