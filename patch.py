with open("frontend/src/components/SetupScreen.tsx", "r") as f:
    code = f.read()
    
target = """            <button 
              onClick={handleStart}
              disabled={fwFiles.length === 0 && code.trim() === ''}
              className="relative overflow-hidden group px-8 py-3 rounded-lg font-bold tracking-wide text-white disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 transition-all flex items-center gap-2"
            >"""

replacement = """            <div className="flex items-center gap-3">
              <button
                onClick={() => setFastMode(!fastMode)}
                className={`w-2 h-2 rounded-full transition-colors ${fastMode ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' : 'bg-white/10 hover:bg-white/30'}`}
                title="Toggle Deterministic Mock Mode"
              />
              <button 
                onClick={handleStart}
                disabled={fwFiles.length === 0 && code.trim() === ''}
                className="relative overflow-hidden group px-8 py-3 rounded-lg font-bold tracking-wide text-white disabled:opacity-50 disabled:cursor-not-allowed bg-blue-600 hover:bg-blue-500 transition-all flex items-center gap-2"
              >"""

code = code.replace(target, replacement)
code = code.replace("            </button>\n          </div>", "            </button>\n            </div>\n          </div>")

with open("frontend/src/components/SetupScreen.tsx", "w") as f:
    f.write(code)
