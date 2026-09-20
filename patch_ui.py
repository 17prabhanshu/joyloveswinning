import re

with open("frontend/src/components/TestLab.tsx", "r") as f:
    code = f.read()

target = """                <div className="grid grid-cols-2 gap-6">
                  <div className="bg-[#0f0f0f] p-5 rounded-xl border border-white/5 shadow-inner">"""

replacement = """                <div className={`grid gap-6 ${selectedTest.minimized ? 'grid-cols-3' : 'grid-cols-2'}`}>
                  {selectedTest.minimized && (
                    <div className="bg-[#1a0f0f] p-5 rounded-xl border border-red-500/20 shadow-inner relative overflow-hidden group">
                      <div className="absolute top-0 right-0 w-16 h-16 bg-red-500/10 rounded-full blur-xl -mr-8 -mt-8"></div>
                      <p className="text-xs text-red-400 font-bold uppercase tracking-widest mb-2 flex items-center gap-1">
                        <Zap size={12} className="animate-pulse" /> Delta Minimizer
                      </p>
                      <p className="font-mono text-red-300 text-[11px] leading-tight">
                        Reduced from <span className="font-bold text-white px-1">{selectedTest.minimized.original}</span> to <span className="font-bold text-white px-1">{selectedTest.minimized.reduced}</span> critical steps to trigger failure.
                      </p>
                    </div>
                  )}
                  <div className="bg-[#0f0f0f] p-5 rounded-xl border border-white/5 shadow-inner">"""

code = code.replace(target, replacement)

with open("frontend/src/components/TestLab.tsx", "w") as f:
    f.write(code)
