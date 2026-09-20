from typing import List, Dict, Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from enum import Enum
from .models import FunctionInfo

class CFGNodeType(str, Enum):
    ENTRY = "ENTRY"
    BLOCK = "BLOCK"
    CONDITION = "CONDITION"
    LOOP = "LOOP"
    EXIT = "EXIT"

class CFGNode(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    id: str
    type: CFGNodeType
    statements: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)

class CFGEdge(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    source: str
    target: str
    condition: Optional[str] = None

class ControlFlowGraph(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    nodes: Dict[str, CFGNode] = Field(default_factory=dict)
    edges: List[CFGEdge] = Field(default_factory=list)
    entry: str = ""
    exits: List[str] = Field(default_factory=list)

class CFGBuilder:
    """Builds a Control Flow Graph for a specific function."""
    def __init__(self):
        self.cfg = ControlFlowGraph()
        
    def build(self, func_info: FunctionInfo) -> ControlFlowGraph:
        entry_id = "entry"
        exit_id = "exit"
        
        self.cfg.nodes[entry_id] = CFGNode(id=entry_id, type=CFGNodeType.ENTRY)
        self.cfg.nodes[exit_id] = CFGNode(id=exit_id, type=CFGNodeType.EXIT)
        self.cfg.entry = entry_id
        self.cfg.exits.append(exit_id)
        
        # Basic implementation that just links entry to exit
        # A more advanced implementation would walk the AST body of the function
        self.cfg.edges.append(CFGEdge(source=entry_id, target=exit_id))
        
        return self.cfg
