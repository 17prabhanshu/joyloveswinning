"""
Failure diagnosis and localization.

Maps deterministic test failures back to firmware source code.
"""
import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from firmware_agent.verification.verifier import VerificationResult, VerificationStatus
from firmware_agent.analyzer.models import FirmwareModel
from firmware_agent.analyzer.behavior import BehaviorGraph

logger = logging.getLogger(__name__)


class ProbableCause(BaseModel):
    description: str
    evidence: List[str]
    confidence: float = Field(ge=0.0, le=1.0)


class SourceLocation(BaseModel):
    file: str
    line: int
    function: str
    code_snippet: str
    suspicion_score: float = Field(ge=0.0, le=1.0)


class DiagnosisResult(BaseModel):
    test_id: str
    failure_type: str
    observed_behavior: str
    expected_behavior: str
    probable_causes: List[ProbableCause]
    source_locations: List[SourceLocation]
    evidence: List[Dict[str, Any]]
    confidence: float = Field(ge=0.0, le=1.0)
    recommendations: List[str]


class FailureLocalizer:
    """Localizes failures to source code using static analysis metadata."""

    def diagnose(self, 
                 verification_result: VerificationResult, 
                 firmware_model: FirmwareModel, 
                 behavior_graph: Optional[BehaviorGraph] = None) -> DiagnosisResult:
        
        if verification_result.passed:
            return DiagnosisResult(
                test_id=verification_result.test_id,
                failure_type="None",
                observed_behavior="Passed all assertions",
                expected_behavior="Passed all assertions",
                probable_causes=[],
                source_locations=[],
                evidence=[],
                confidence=1.0,
                recommendations=["None required, test passed."]
            )

        failed_assertions = [a for a in verification_result.assertions if not a.passed]
        
        failure_type = "Multiple Failures"
        if len(failed_assertions) == 1:
            failure_type = failed_assertions[0].assertion_type

        # Extract context
        observed = verification_result.uart_output[-200:] if verification_result.uart_output else verification_result.stop_reason
        expected = "; ".join([f"{a.assertion_type} = {a.expected}" for a in failed_assertions])

        causes = []
        locations = []
        
        # Heuristic 1: If it's a GPIO failure, find functions that modify that GPIO
        gpio_failures = [a for a in failed_assertions if 'gpio' in a.assertion_type]
        if gpio_failures:
            causes.append(ProbableCause(
                description="GPIO state did not match expected value",
                evidence=[a.description for a in gpio_failures],
                confidence=0.8
            ))
            locations.extend(self._find_functions_with_io(firmware_model, "gpio"))

        # Heuristic 2: If it's a UART failure, find functions that print
        uart_failures = [a for a in failed_assertions if 'uart' in a.assertion_type]
        if uart_failures:
            causes.append(ProbableCause(
                description="UART output did not match expected pattern",
                evidence=[a.description for a in uart_failures],
                confidence=0.8
            ))
            locations.extend(self._find_functions_with_io(firmware_model, "uart"))
            
        # Heuristic 3: Check boundary condition failures
        # If the test scenario was a boundary test (we can check the test ID if it contains 'TS_')
        # We can look for boundary conditions in the firmware model
        if behavior_graph and behavior_graph.boundary_conditions:
            locations.extend(self._find_functions_with_conditions(firmware_model, behavior_graph.boundary_conditions))
            
        # Deduplicate locations and sort by score
        unique_locs = {}
        for loc in locations:
            key = f"{loc.file}:{loc.line}:{loc.function}"
            if key not in unique_locs or loc.suspicion_score > unique_locs[key].suspicion_score:
                unique_locs[key] = loc
                
        sorted_locations = sorted(unique_locs.values(), key=lambda x: x.suspicion_score, reverse=True)

        if not causes:
            causes.append(ProbableCause(
                description="Simulation aborted or failed unexpectedly",
                evidence=[verification_result.failure_reason],
                confidence=0.5
            ))

        return DiagnosisResult(
            test_id=verification_result.test_id,
            failure_type=failure_type,
            observed_behavior=observed,
            expected_behavior=expected,
            probable_causes=causes,
            source_locations=sorted_locations[:5], # Top 5
            evidence=verification_result.evidence_chain,
            confidence=0.7,
            recommendations=["Review the highlighted source code for boundary errors or missing logic."]
        )

    def _find_functions_with_io(self, model: FirmwareModel, io_type: str) -> List[SourceLocation]:
        locations = []
        for func in model.functions:
            ops = func.gpio_ops if io_type == "gpio" else func.uart_ops
            if ops:
                locations.append(SourceLocation(
                    file=model.file_path,
                    line=func.start_line,
                    function=func.name,
                    code_snippet=f"{func.name}(...) {{ ... }}",
                    suspicion_score=0.6
                ))
        return locations

    def _find_functions_with_conditions(self, model: FirmwareModel, conditions: List[str]) -> List[SourceLocation]:
        locations = []
        for func in model.functions:
            if func.conditions:
                locations.append(SourceLocation(
                    file=model.file_path,
                    line=func.start_line,
                    function=func.name,
                    code_snippet=f"Conditions: {', '.join(func.conditions[:2])}",
                    suspicion_score=0.7
                ))
        return locations
