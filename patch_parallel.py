import re

with open("ps3_agent/core/loop.py", "r") as f:
    code = f.read()

# Replace the sequential loop with a parallel one.
target = """        for candidate in selected:
            if tests_executed >= self.max_tests:
                self.stopping_reason = "Test budget exhausted"
                break

            scenario = candidate.scenario
            tests_executed += 1"""

replacement = """        import concurrent.futures
        import threading
        
        lock = threading.Lock()
        
        def run_candidate(candidate):
            scenario = candidate.scenario

            # Emit planning decision
            self._emit(
                "PLANNER", AgentAction.PLAN,
                f"Selected test {scenario.test_id}: {scenario.why_this_test_exists}",
                outputs={"test_id": scenario.test_id, "target": scenario.target,
                         "priority": candidate.value_score},
            )

            # Execute
            t0 = time.monotonic()
            prepared = simulator.prepare(self.firmware_path, scenario, "/tmp")
            execution = simulator.execute(prepared)
            dt = (time.monotonic() - t0) * 1000

            self._emit(
                "EXECUTOR", AgentAction.EXECUTE,
                f"Executed {scenario.test_id} on {simulator.name()} ({dt:.1f}ms)",
                outputs={"uart_lines": len(execution.uart),
                         "gpio": execution.gpio,
                         "exit_status": execution.exit_status},
                duration_ms=dt,
            )

            # Verify
            t0 = time.monotonic()
            verification = verify(scenario, execution)
            dt = (time.monotonic() - t0) * 1000

            status_str = verification.status.value
            self._emit(
                "VERIFIER", AgentAction.VERIFY,
                f"{scenario.test_id}: {status_str.upper()}",
                outputs={"status": status_str,
                         "assertions": len(verification.assertions)},
                duration_ms=dt,
                status=status_str,
            )

            with lock:
                # Record result
                self.regression_memory.record_result(
                    scenario.test_id, scenario, verification, execution
                )

            result_entry: dict[str, Any] = {
                "test_id": scenario.test_id,
                "scenario": scenario,
                "execution": execution,
                "verification": verification,
                "diagnosis": None,
                "minimized": None,
                "regression": None,
            }
            
            return candidate, execution, verification, result_entry

        futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            for candidate in selected[:self.max_tests]:
                futures.append(executor.submit(run_candidate, candidate))
                
            for future in concurrent.futures.as_completed(futures):
                candidate, execution, verification, result_entry = future.result()
                scenario = candidate.scenario
                tests_executed += 1"""

code = code.replace(target, replacement)
code = code.replace("            previous_result = verification", "")

# Remove the old execute/verify code since it's now in run_candidate
target2 = """            # Emit planning decision
            self._emit(
                "PLANNER", AgentAction.PLAN,
                f"Selected test {scenario.test_id}: {scenario.why_this_test_exists}",
                outputs={"test_id": scenario.test_id, "target": scenario.target,
                         "priority": candidate.value_score},
            )

            # Execute
            t0 = time.monotonic()
            prepared = simulator.prepare(self.firmware_path, scenario, "/tmp")
            execution = simulator.execute(prepared)
            dt = (time.monotonic() - t0) * 1000

            self._emit(
                "EXECUTOR", AgentAction.EXECUTE,
                f"Executed {scenario.test_id} on {simulator.name()} ({dt:.1f}ms)",
                outputs={"uart_lines": len(execution.uart),
                         "gpio": execution.gpio,
                         "exit_status": execution.exit_status},
                duration_ms=dt,
            )

            # Verify
            t0 = time.monotonic()
            verification = verify(scenario, execution)
            dt = (time.monotonic() - t0) * 1000

            status_str = verification.status.value
            self._emit(
                "VERIFIER", AgentAction.VERIFY,
                f"{scenario.test_id}: {status_str.upper()}",
                outputs={"status": status_str,
                         "assertions": len(verification.assertions)},
                duration_ms=dt,
                status=status_str,
            )

            # Record result
            self.regression_memory.record_result(
                scenario.test_id, scenario, verification, execution
            )

            result_entry: dict[str, Any] = {
                "test_id": scenario.test_id,
                "scenario": scenario,
                "execution": execution,
                "verification": verification,
                "diagnosis": None,
                "minimized": None,
                "regression": None,
            }"""

code = code.replace(target2, "")


with open("ps3_agent/core/loop.py", "w") as f:
    f.write(code)
