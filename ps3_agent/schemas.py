from __future__ import annotations
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

# 1. Enums
class RiskCategory(str, Enum):
    BOUNDARY = "BOUNDARY"
    ASSUMPTION = "ASSUMPTION"
    STATE = "STATE"
    FAULT = "FAULT"
    TIMING = "TIMING"
    INPUT = "INPUT"
    HARDWARE = "HARDWARE"
    RECOVERY = "RECOVERY"
    ERROR_HANDLING = "ERROR_HANDLING"

class RiskSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class ExplorationStatus(str, Enum):
    UNEXPLORED = "UNEXPLORED"
    PARTIAL = "PARTIAL"
    EXPLORED = "EXPLORED"

class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    SKIPPED = "SKIPPED"
    UNSUPPORTED = "UNSUPPORTED"
    UNCERTAIN = "UNCERTAIN"
    SIMULATOR_DISAGREEMENT = "SIMULATOR_DISAGREEMENT"

class AssertionProvenance(str, Enum):
    SPECIFICATION = "SPECIFICATION"
    EXPLICIT_TEST = "EXPLICIT_TEST"
    FIRMWARE_ASSERTION = "FIRMWARE_ASSERTION"
    DERIVED_RULE = "DERIVED_RULE"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"

class AgentAction(str, Enum):
    ANALYZE = "ANALYZE"
    MODEL = "MODEL"
    HUNT_BOUNDARIES = "HUNT_BOUNDARIES"
    HUNT_ASSUMPTIONS = "HUNT_ASSUMPTIONS"
    HUNT_STATES = "HUNT_STATES"
    INJECT_FAULTS = "INJECT_FAULTS"
    PLAN = "PLAN"
    GENERATE = "GENERATE"
    RANK = "RANK"
    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    VERIFY = "VERIFY"
    DIAGNOSE = "DIAGNOSE"
    MINIMIZE = "MINIMIZE"
    REGRESS = "REGRESS"
    UPDATE_KNOWLEDGE = "UPDATE_KNOWLEDGE"
    SELECT_NEXT = "SELECT_NEXT"

# Base configuration class for consistent Pydantic model settings
class PS3BaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# 2. Firmware Models
class FirmwareProject(PS3BaseModel):
    id: str
    name: str
    source_files: List[str] = Field(default_factory=list)
    firmware_hash: str
    created_at: str

class FirmwareSymbol(PS3BaseModel):
    name: str
    kind: str
    file: Optional[str] = None
    line: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    hw_interactions: List[str] = Field(default_factory=list)

class FirmwareUnderstanding(PS3BaseModel):
    project_id: str
    functions: List[FirmwareSymbol] = Field(default_factory=list)
    variables: List[str] = Field(default_factory=list)
    constants: Dict[str, Any] = Field(default_factory=dict)
    io_points: List[str] = Field(default_factory=list)
    state_variables: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    error_handlers: List[str] = Field(default_factory=list)

# 3. Behavior Models
class BehaviorNode(PS3BaseModel):
    id: str
    label: str
    kind: str
    file: Optional[str] = None
    line: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BehaviorEdge(PS3BaseModel):
    source: str
    target: str
    kind: str
    condition: Optional[str] = None

class BehaviorGraph(PS3BaseModel):
    nodes: List[BehaviorNode] = Field(default_factory=list)
    edges: List[BehaviorEdge] = Field(default_factory=list)

# 4. Risk Models
class RiskFinding(PS3BaseModel):
    risk_id: str
    category: RiskCategory
    source_location: Optional[str] = None
    explanation: str
    severity: RiskSeverity
    confidence: float
    exploration_status: ExplorationStatus
    related_tests: List[str] = Field(default_factory=list)
    contributing_factors: List[str] = Field(default_factory=list)

class AssumptionFinding(PS3BaseModel):
    id: str
    description: str
    source_location: Optional[str] = None
    attack_scenario: Optional[str] = None
    severity: RiskSeverity

# 5. Test Models
class TestScenario(PS3BaseModel):
    test_id: str
    target: str
    category: str
    reason: str
    expected_outcome: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    priority: float
    why_this_test_exists: str
    information_value: str

class TestCandidate(PS3BaseModel):
    scenario: TestScenario
    value_score: float
    novelty_score: float
    risk_score: float
    redundancy_score: float
    selected: bool = False

# 6. Execution Models
class ExecutionResult(PS3BaseModel):
    run_id: str
    simulator: str
    simulator_version: str
    firmware_hash: str
    scenario_hash: str
    started_at: str
    duration_ms: float
    exit_status: str
    uart: List[str] = Field(default_factory=list)
    gpio: Dict[str, Any] = Field(default_factory=dict)
    sensors: Dict[str, Any] = Field(default_factory=dict)
    registers: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    timeout: bool = False
    fidelity_notes: Optional[str] = None

# 7. Verification Models
class Assertion(PS3BaseModel):
    type: str
    expected: Any
    observed: Optional[Any] = None
    provenance: AssertionProvenance
    verdict: Optional[VerificationStatus] = None
    evidence: Optional[str] = None

class VerificationResult(PS3BaseModel):
    test_id: str
    status: VerificationStatus
    assertions: List[Assertion] = Field(default_factory=list)
    evidence_chain: List[Dict[str, Any]] = Field(default_factory=list)

# 8. Diagnosis Models
class DiagnosisResult(PS3BaseModel):
    test_id: str
    failed_assertion: Optional[str] = None
    hardware_signal: Optional[str] = None
    firmware_operation: Optional[str] = None
    function_name: Optional[str] = None
    source_location: Optional[str] = None
    relevant_condition: Optional[str] = None
    cause_hypothesis: str
    confidence: float
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    is_hypothesis: bool = True

# 9. Minimization
class MinimizedFailure(PS3BaseModel):
    original_steps: int
    minimized_steps: int
    original_scenario: TestScenario
    minimized_scenario: TestScenario
    minimization_log: List[str] = Field(default_factory=list)

# 10. Regression
class RegressionTest(PS3BaseModel):
    regression_id: str
    firmware_hash: str
    scenario: TestScenario
    expected_behavior: str
    observed_failure: str
    source_location: Optional[str] = None
    created_at: str
    simulator: str
    minimized_reproducer: Optional[TestScenario] = None
    confirmed: bool = False

# 11. Agent Models
class AgentEvent(PS3BaseModel):
    event_id: str
    run_id: str
    timestamp: str
    agent: str
    action: AgentAction
    reason: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float
    status: str

class AgentDecision(PS3BaseModel):
    decision: str
    target: str
    reason: List[str] = Field(default_factory=list)
    expected_information: List[str] = Field(default_factory=list)
    previous_result: Optional[str] = None

class AgentMemory(PS3BaseModel):
    discovered_risks: List[RiskFinding] = Field(default_factory=list)
    explored_states: List[str] = Field(default_factory=list)
    covered_branches: List[str] = Field(default_factory=list)
    failures: List[str] = Field(default_factory=list)
    regressions: List[str] = Field(default_factory=list)
    simulator_disagreements: List[str] = Field(default_factory=list)
    assumptions: List[AssumptionFinding] = Field(default_factory=list)
    previous_results: List[Dict[str, Any]] = Field(default_factory=list)
    useful_patterns: List[str] = Field(default_factory=list)

# 12. Simulator
class SimulatorComparison(PS3BaseModel):
    scenario_id: str
    simulators: List[str] = Field(default_factory=list)
    uart_match: bool
    gpio_match: bool
    state_match: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    verdict: str

# 13. Run
class RunSummary(PS3BaseModel):
    run_id: str
    project_id: str
    status: str
    firmware_hash: str
    started_at: str
    completed_at: Optional[str] = None
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    risks_found: int = 0
    risks_explored: int = 0
    failures_found: int = 0
    regressions_created: int = 0
    stopping_reason: Optional[str] = None
    agent_events: List[AgentEvent] = Field(default_factory=list)
