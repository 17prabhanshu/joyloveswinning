        self._emit(
            "SCENARIO_ENGINE", AgentAction.GENERATE,
            f"Generated {len(self.all_scenarios)} test scenarios, ranked by risk",
            duration_ms=dt,
        )

        # ── Phase 5: Execute Loop ──────────────────────────────
        from ps3_agent.execution.simulator import get_default_simulator, DeterministicSimulator
        from ps3_agent.verification.verifier import verify
        from ps3_agent.diagnosis.investigator import diagnose_failure
        from ps3_agent.planner.adaptive import select_next_test

        if self.fast_mode:
            simulator = DeterministicSimulator()
        else:
            simulator = get_default_simulator()
            
        selected = [c for c in self.candidates if c.selected]
        tests_executed = 0
        passed = 0
        failed = 0
        errors = 0

        previous_result: Optional[VerificationResult] = None

        for candidate in selected:
            if tests_executed >= self.max_tests:
                self.stopping_reason = "Test budget exhausted"
                break

            scenario = candidate.scenario
            tests_executed += 1

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
            previous_result = verification

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
            }

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

            # Adaptive next-test selection
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

