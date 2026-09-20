"""
Autonomous Firmware Red-Team Agent — Core Loop.

This is the heart of the system. It implements the closed loop:

    ANALYZE → MODEL → RISK → GENERATE → RANK → EXECUTE →
    OBSERVE → VERIFY → DIAGNOSE → MINIMIZE → REGRESS →
    UPDATE KNOWLEDGE → SELECT NEXT → REPEAT
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from ps3_agent.schemas import (
    AgentAction,
    AgentDecision,
    AgentEvent,
    AgentMemory,
    BehaviorGraph,
    DiagnosisResult,
    ExecutionResult,
    FirmwareProject,
    FirmwareUnderstanding,
    MinimizedFailure,
    RegressionTest,
    RiskFinding,
    RunSummary,
    TestCandidate,
    TestScenario,
    VerificationResult,
    VerificationStatus,
)

logger = logging.getLogger(__name__)


class AgentLoop:
    """
    The autonomous firmware red-team agent.

    Orchestrates the full closed-loop cycle:
    firmware understanding → risk assessment → test generation →
    execution → verification → diagnosis → minimization →
    regression → adaptive next-test selection.
    """

    def __init__(
        self,
        project: FirmwareProject,
        firmware_path: str,
        max_tests: int = 30,
        fast_mode: bool = False,
        on_event: Optional[Callable[[AgentEvent], None]] = None,
    ):
        self.project = project
        self.firmware_path = firmware_path
        self.max_tests = max_tests
        self.fast_mode = fast_mode
        self.on_event = on_event or (lambda e: None)

        self.run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.status = "idle"
        self.events: list[AgentEvent] = []
        self.test_results: list[dict[str, Any]] = []
        self.risks: list[RiskFinding] = []
        self.understanding: Optional[FirmwareUnderstanding] = None
        self.behavior_graph: Optional[BehaviorGraph] = None
        self.all_scenarios: list[TestScenario] = []
        self.candidates: list[TestCandidate] = []
        self.failures: list[dict[str, Any]] = []
        self.regressions: list[RegressionTest] = []
        self.stopping_reason: Optional[str] = None

        # Late imports to avoid circular dependencies
        from ps3_agent.regression.memory import RegressionMemory
        self.regression_memory = RegressionMemory()

    def _emit(self, agent: str, action: AgentAction, reason: str,
              inputs: dict | None = None, outputs: dict | None = None,
              duration_ms: float = 0, status: str = "ok") -> AgentEvent:
        event = AgentEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            run_id=self.run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            agent=agent,
            action=action,
            reason=reason,
            inputs=inputs or {},
            outputs=outputs or {},
            duration_ms=duration_ms,
            status=status,
        )
        self.events.append(event)
        self.on_event(event)
        logger.info(f"[{agent}] {action.value}: {reason}")
        return event

    def run(self) -> RunSummary:
        """Execute the full autonomous loop."""
        self.status = "running"
        self._emit("AGENT", AgentAction.ANALYZE, "Starting autonomous firmware analysis")

        # ── Phase 1: Analyze ──────────────────────────────────
        t0 = time.monotonic()
        from ps3_agent.firmware.analyzer import analyze_firmware
        self.understanding = analyze_firmware(self.project)
        dt = (time.monotonic() - t0) * 1000
        self._emit(
            "CODE_READER", AgentAction.ANALYZE,
            f"Parsed {len(self.understanding.functions)} functions, "
            f"{len(self.understanding.conditions)} conditions, "
            f"{len(self.understanding.io_points)} I/O points",
            outputs={
                "functions": len(self.understanding.functions),
                "conditions": len(self.understanding.conditions),
                "io_points": len(self.understanding.io_points),
                "state_vars": len(self.understanding.state_variables),
            },
            duration_ms=dt,
        )

        # ── Phase 2: Build Behavior Model ─────────────────────
        t0 = time.monotonic()
        from ps3_agent.behavior.graph_builder import build_behavior_graph
        self.behavior_graph = build_behavior_graph(self.understanding)
        dt = (time.monotonic() - t0) * 1000
        self._emit(
            "MODELER", AgentAction.MODEL,
            f"Built behavior graph: {len(self.behavior_graph.nodes)} nodes, "
            f"{len(self.behavior_graph.edges)} edges",
            duration_ms=dt,
        )

        # ── Phase 3: Assess Risks ─────────────────────────────
        t0 = time.monotonic()
        from ps3_agent.risk.engine import assess_risks
        self.risks = assess_risks(self.understanding, self.behavior_graph)
        dt = (time.monotonic() - t0) * 1000

        high_risks = [r for r in self.risks if r.severity.value == "HIGH"]
        self._emit(
            "RISK_ENGINE", AgentAction.HUNT_BOUNDARIES,
            f"Identified {len(self.risks)} risks ({len(high_risks)} HIGH)",
            outputs={"total_risks": len(self.risks), "high": len(high_risks)},
            duration_ms=dt,
        )

        for risk in self.risks:
            self._emit(
                f"{risk.category.value}_HUNTER",
                AgentAction.HUNT_BOUNDARIES,
                f"[{risk.severity.value}] {risk.explanation}",
                outputs={"risk_id": risk.risk_id, "source": risk.source_location},
            )

        # ── Phase 4: Generate Scenarios ────────────────────────
        t0 = time.monotonic()
        from ps3_agent.scenarios.generator import generate_scenarios, rank_candidates
        memory = self.regression_memory.get_memory()
        self.all_scenarios = generate_scenarios(self.risks, self.understanding, memory)
        self.candidates = rank_candidates(self.all_scenarios, memory)
        dt = (time.monotonic() - t0) * 1000
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

        import concurrent.futures
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=30) as executor:
            for candidate in selected[:self.max_tests]:
                futures.append(executor.submit(run_candidate, candidate))
                
            for future in concurrent.futures.as_completed(futures):
                candidate, execution, verification, result_entry = future.result()
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

        # ── Phase 6: Completion ────────────────────────────────
        if not self.stopping_reason:
            unexplored_high = [
                r for r in self.risks
                if r.severity.value == "HIGH"
                and r.exploration_status.value == "UNEXPLORED"
            ]
            if not unexplored_high:
                self.stopping_reason = "All high-priority risks explored"
            else:
                self.stopping_reason = "All generated tests executed"

        self.status = "completed"
        self._emit(
            "AGENT", AgentAction.UPDATE_KNOWLEDGE,
            f"Run complete. {tests_executed} tests, {failed} failures, "
            f"{len(self.regressions)} regressions. "
            f"Stopping: {self.stopping_reason}",
        )

        return RunSummary(
            run_id=self.run_id,
            project_id=self.project.id,
            status="completed",
            firmware_hash=hashlib.sha256(
                Path(self.firmware_path).read_bytes()
            ).hexdigest()[:16],
            started_at=self.started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
            total_tests=tests_executed,
            passed=passed,
            failed=failed,
            errors=errors,
            risks_found=len(self.risks),
            risks_explored=len([
                r for r in self.risks
                if r.exploration_status.value != "UNEXPLORED"
            ]),
            failures_found=failed,
            regressions_created=len(self.regressions),
            stopping_reason=self.stopping_reason,
            agent_events=self.events,
        )
