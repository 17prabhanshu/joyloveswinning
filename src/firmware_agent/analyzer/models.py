from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Optional

class VariableInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    type: str
    is_global: bool = False
    is_const: bool = False
    value: Optional[str] = None
    line: int

class StructField(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    type: str

class StructInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    fields: List[StructField] = Field(default_factory=list)
    line: int

class EnumValue(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    value: Optional[str] = None

class EnumInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    values: List[EnumValue] = Field(default_factory=list)
    line: int

class DefineInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    value: Optional[str] = None
    line: int

class FunctionInfo(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    params: List[Dict[str, str]] = Field(default_factory=list)
    return_type: str
    start_line: int
    end_line: int
    body_text: str = ""
    calls: List[str] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    loops: List[str] = Field(default_factory=list)
    gpio_ops: List[str] = Field(default_factory=list)
    uart_ops: List[str] = Field(default_factory=list)
    sensor_reads: List[str] = Field(default_factory=list)
    timer_ops: List[str] = Field(default_factory=list)
    isr_markers: List[str] = Field(default_factory=list)

class FirmwareModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    functions: List[FunctionInfo] = Field(default_factory=list)
    variables: List[VariableInfo] = Field(default_factory=list)
    structs: List[StructInfo] = Field(default_factory=list)
    enums: List[EnumInfo] = Field(default_factory=list)
    defines: List[DefineInfo] = Field(default_factory=list)
    includes: List[str] = Field(default_factory=list)
    file_path: str
