from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class Category(str, Enum):
    NORMAL = "NORMAL"
    BOUNDARY = "BOUNDARY"
    INVALID = "INVALID"
    FAULT_INJECTION = "FAULT_INJECTION"
    STATE_TRANSITION = "STATE_TRANSITION"
    TIMING = "TIMING"
    SEQUENCE = "SEQUENCE"
    REGRESSION = "REGRESSION"
    FUZZ = "FUZZ"

class TestInput(BaseModel):
    name: str
    value: Any
    type: str = 'sensor'

class ExpectedOutput(BaseModel):
    type: str
    target: str
    value: Any
    condition: str = 'equals'

class TestScenario(BaseModel):
    test_id: str
    category: Category
    target_function: str
    description: str
    inputs: List[TestInput]
    expected_outputs: List[ExpectedOutput]
    reason: str
    priority: int = 5
    source_file: Optional[str] = None

class TestSuite(BaseModel):
    scenarios: List[TestScenario]
    firmware_path: str
    generated_at: str
    generator: str
