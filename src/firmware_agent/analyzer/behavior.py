from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from .models import FirmwareModel, FunctionInfo

class NodeType(str, Enum):
    INPUT = "INPUT"
    FUNCTION = "FUNCTION"
    CONDITION = "CONDITION"
    STATE_CHANGE = "STATE_CHANGE"
    OUTPUT = "OUTPUT"
    ERROR = "ERROR"

class BehaviorNode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    type: NodeType
    label: str
    source_location: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class BehaviorEdge(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    source: str
    target: str
    condition: Optional[str] = None
    label: Optional[str] = None

class BehaviorGraph(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    nodes: Dict[str, BehaviorNode] = Field(default_factory=dict)
    edges: List[BehaviorEdge] = Field(default_factory=list)
    boundary_conditions: List[str] = Field(default_factory=list)
    state_transitions: List[Dict[str, str]] = Field(default_factory=list)
    io_operations: List[str] = Field(default_factory=list)

class BehaviorGraphBuilder:
    """Builds a behavior graph from a FirmwareModel."""
    def __init__(self):
        self.graph = BehaviorGraph()
        
    def build(self, model: FirmwareModel) -> BehaviorGraph:
        for func in model.functions:
            self._process_function(func)
        return self.graph
        
    def _process_function(self, func: FunctionInfo):
        func_node_id = f"func_{func.name}"
        self.graph.nodes[func_node_id] = BehaviorNode(
            id=func_node_id,
            type=NodeType.FUNCTION,
            label=func.name,
            source_location=func.start_line
        )
        
        # IO Operations
        for op in func.gpio_ops:
            op_id = f"gpio_{len(self.graph.nodes)}"
            self.graph.nodes[op_id] = BehaviorNode(
                id=op_id, type=NodeType.OUTPUT, label=op
            )
            self.graph.edges.append(BehaviorEdge(source=func_node_id, target=op_id))
            self.graph.io_operations.append(op)
            
        for cond in func.conditions:
            cond_id = f"cond_{len(self.graph.nodes)}"
            self.graph.nodes[cond_id] = BehaviorNode(
                id=cond_id, type=NodeType.CONDITION, label="if(...)"
            )
            self.graph.edges.append(BehaviorEdge(source=func_node_id, target=cond_id))
            
            # Simple boundary condition extraction
            if any(op in cond for op in [">=", "<=", "==", "<", ">"]):
                self.graph.boundary_conditions.append(cond)
