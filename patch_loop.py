import re

with open("ps3_agent/core/loop.py", "r") as f:
    code = f.read()

# Replace the loop with a ThreadPoolExecutor loop
target = """        for candidate in selected:
            if tests_executed >= self.max_tests:
                self.stopping_reason = "Test budget exhausted"
                break

            scenario = candidate.scenario
            tests_executed += 1"""

replacement = """        import concurrent.futures
        
        # Parallel Execution Engine
        def run_test(candidate):
            scenario = candidate.scenario
            return scenario, candidate
            
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_cand = {executor.submit(run_test, c): c for c in selected[:self.max_tests]}
            
            for future in concurrent.futures.as_completed(future_to_cand):
                scenario, candidate = future.result()
                tests_executed += 1"""

code = code.replace(target, replacement)

with open("ps3_agent/core/loop.py", "w") as f:
    f.write(code)
