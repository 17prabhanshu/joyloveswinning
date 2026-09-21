import re

with open("ps3_agent/core/loop.py", "r") as f:
    content = f.read()

# We will replace from Phase 5 to Phase 6 with the correct threaded loop
start_marker = "# ── Phase 5: Execute Loop ──────────────────────────────"
end_marker = "# ── Phase 6: Completion ────────────────────────────────"

new_phase_5 = """# ── Phase 5: Execute Loop ──────────────────────────────
        from ps3_agent.execution.simulator import get_default_simulator
        from ps3_agent.verification.verifier import verify
        from ps3_agent.diagnosis.investigator import diagnose_failure
        from ps3_agent.planner.adaptive import select_next_test

        simulator = get_default_simulator()
            
        selected = [c for c in self.candidates if c.selected]
        tests_executed = 0
        passed = 0
        failed = 0
        errors = 0

        previous_result = None

        import concurrent.futures
        import threading
        import time
        import hashlib
        from pathlib import Path
        from ps3_agent.schemas import AgentAction, VerificationStatus
        
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
                # Record result safely
                self.regression_memory.record_result(
                    scenario.test_id, scenario, verification, execution
                )

            result_entry = {
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
                tests_executed += 1

                if verification.status == VerificationStatus.PASS:
                    passed += 1
                elif verification.status == VerificationStatus.FAIL:
                    failed += 1

                    # Diagnose
                    t0 = time.monotonic()
                    diagnosis = diagnose_failure(
                        scenario, execution, verification, self.understanding
                    )
                    dt = (time.monotonic() - t0) * 1000
                    result_entry["diagnosis"] = diagnosis

                    self._emit(
                        "DIAGNOSER", AgentAction.DIAGNOSE,
                        f"Likely cause: {diagnosis.cause_hypothesis}",
                        outputs={
                            "function": diagnosis.function_name,
                            "source": diagnosis.source_location,
                            "condition": diagnosis.relevant_condition,
                            "confidence": diagnosis.confidence,
                        },
                        duration_ms=dt,
                    )

                    # Minimize
                    t0 = time.monotonic()
                    minimized = self.regression_memory.minimize_failure(
                        scenario,
                        lambda s: verify(s, simulator.execute(
                            simulator.prepare(self.firmware_path, s, "/tmp")
                        )),
                    )
                    dt = (time.monotonic() - t0) * 1000
                    result_entry["minimized"] = minimized

                    self._emit(
                        "MINIMIZER", AgentAction.MINIMIZE,
                        f"Reduced from {minimized.original_steps} to "
                        f"{minimized.minimized_steps} events",
                        duration_ms=dt,
                    )

                    # Create regression
                    firmware_hash = hashlib.sha256(
                        Path(self.firmware_path).read_bytes()
                    ).hexdigest()[:16]
                    regression = self.regression_memory.create_regression(
                        scenario, verification, diagnosis,
                        firmware_hash, simulator.name(),
                    )
                    result_entry["regression"] = regression
                    self.regressions.append(regression)

                    self._emit(
                        "REGRESSION", AgentAction.REGRESS,
                        f"Created {regression.regression_id}",
                        outputs={"regression_id": regression.regression_id},
                    )

                    self.failures.append(result_entry)
                else:
                    errors += 1

                self.test_results.append(result_entry)

        # Adaptive next-test selection outside the loop when all are done
        memory = self.regression_memory.get_memory()
        decision = select_next_test(memory, self.risks, previous_result)
        self._emit(
            "ADAPTIVE_AGENT", AgentAction.SELECT_NEXT,
            f"Next: {decision.target} — {', '.join(decision.reason)}",
            outputs={
                "decision": decision.decision,
                "target": decision.target,
                "reasons": decision.reason,
            },
        )

        """

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

new_content = content[:start_idx] + new_phase_5 + content[end_idx:]

with open("ps3_agent/core/loop.py", "w") as f:
    f.write(new_content)

print("Patched loop.py")
