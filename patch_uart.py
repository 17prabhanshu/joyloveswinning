import re

with open("frontend/src/components/TestLab.tsx", "r") as f:
    code = f.read()

target = """                  </motion.div>
                )}
              </div>
            </motion.div>"""

replacement = """                  </motion.div>
                )}
                
                {/* Simulator UART Output */}
                {selectedTest.uart && selectedTest.uart.length > 0 && (
                  <div className="bg-[#0a0a0a] rounded-xl border border-gray-800 overflow-hidden shadow-inner">
                    <div className="bg-gray-900/50 px-4 py-2 border-b border-gray-800 flex justify-between items-center">
                      <p className="text-xs text-gray-500 font-bold uppercase tracking-widest flex items-center gap-2">
                        <Terminal size={14} />
                        Simulator Terminal Log
                      </p>
                      <span className="text-[10px] text-gray-600 font-mono bg-black px-2 py-0.5 rounded">WOKWI EMULATOR</span>
                    </div>
                    <div className="p-4 bg-black overflow-x-auto max-h-64 scrollbar-custom font-mono text-xs leading-relaxed">
                      {selectedTest.uart.map((line: string, i: number) => (
                        <div key={i} className="flex hover:bg-white/5 px-2 py-0.5 rounded transition-colors group">
                          <span className="text-gray-700 w-8 select-none border-r border-gray-800 mr-3 text-right pr-2 group-hover:text-gray-500">{i+1}</span>
                          <span className={line.includes('ERROR') || line.includes('FAIL') ? 'text-red-400' : line.includes('BOOT') ? 'text-green-400 font-bold' : 'text-gray-300'}>
                            {line}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>"""

code = code.replace(target, replacement)

with open("frontend/src/components/TestLab.tsx", "w") as f:
    f.write(code)
