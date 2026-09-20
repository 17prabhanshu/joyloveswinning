"""
Abstract base class for simulator adapters.

Provides a stable interface so the PS3 agent layer does not care
which simulator backend is executing the firmware.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class StopReason(str, Enum):
    """Why the simulation ended."""
    MAX_STEPS = "max_steps"
    MAX_CYCLES = "max_cycles"
    HALT = "halt"
    MEMORY_VIOLATION = "memory_violation"
    DECODE_ERROR = "decode_error"
    EXCEPTION = "exception"
    WALL_TIME = "wall_time"
    MAX_UART_BYTES = "max_uart_bytes"
    NO_PROGRESS = "no_progress"
    ASSERTIONS_PASSED = "assertions_passed"
    CONFIG_ERROR = "config_error"
    UNKNOWN = "unknown"


class AssertionResult(BaseModel):
    """Result of a single assertion check."""
    assertion: dict[str, Any]
    passed: bool


class SimulationResult(BaseModel):
    """Machine-readable result from a single simulation run.

    This mirrors LabWired's result.json schema but is simulator-agnostic.
    """
    status: str  # "pass", "fail", "error"
    steps_executed: int = 0
    cycles: int = 0
    instructions: int = 0
    stop_reason: str = "unknown"
    stop_reason_details: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    assertions: list[AssertionResult] = Field(default_factory=list)
    uart_output: str = ""
    gpio_state: dict[str, Any] = Field(default_factory=dict)
    cpu_state: dict[str, Any] = Field(default_factory=dict)
    memory_state: dict[str, Any] = Field(default_factory=dict)
    raw_result: dict[str, Any] = Field(default_factory=dict)
    firmware_hash: str = ""
    snapshot: dict[str, Any] = Field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    @property
    def failed(self) -> bool:
        return self.status == "fail"

    @property
    def errored(self) -> bool:
        return self.status == "error"


class HardwareConfig(BaseModel):
    """Hardware configuration for a simulation run."""
    chip: str | None = None
    system_manifest: str | None = None
    firmware_path: str = ""
    max_steps: int = 100_000
    max_cycles: int | None = None
    max_uart_bytes: int | None = None
    wall_time_ms: int | None = None
    no_progress_steps: int | None = None
    uart_injections: list[dict[str, Any]] = Field(default_factory=list)
    sensor_inputs: dict[str, float] = Field(default_factory=dict)
    assertions: list[dict[str, Any]] = Field(default_factory=list)
    extra_args: list[str] = Field(default_factory=list)


class SimulatorCapabilities(BaseModel):
    """Capabilities of a simulator backend for a specific chip.

    Fields:
        chip: The chip name this capability set describes.
        available: Whether the chip config was found and parsed successfully.
        error: If not available, a human-readable reason why.
        can_observe_gpio: Whether GPIO state can be observed during simulation.
        can_observe_uart: Whether UART output can be captured.
        can_observe_registers: Whether CPU/peripheral registers can be inspected.
        can_inject_faults: List of supported fault injection modes.
        supported_pins: List of valid pin names (e.g. ["PA0", "PA1", ..., "PC15"]).
    """
    chip: str = ""
    available: bool = False
    error: str = ""
    can_observe_gpio: bool = False
    can_observe_uart: bool = False
    can_observe_registers: bool = False
    can_inject_faults: list[str] = Field(default_factory=list)
    supported_pins: list[str] = Field(default_factory=list)


class SimulatorAdapter(ABC):
    """Abstract simulator adapter interface.

    All simulator backends (LabWired, Wokwi, etc.) must implement this.
    The rest of the PS3 agent operates through this interface only.
    """

    @abstractmethod
    def capabilities(self, chip: str) -> SimulatorCapabilities:
        """Return the capabilities of this simulator for the given chip."""
        ...

    @abstractmethod
    def name(self) -> str:
        """Return the simulator backend name."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this simulator backend is available on the system."""
        ...

    @abstractmethod
    def prepare(self, firmware_path: str | Path, config: HardwareConfig) -> None:
        """Prepare a simulation run (generate test scripts, validate inputs)."""
        ...

    @abstractmethod
    def execute(self, config: HardwareConfig) -> SimulationResult:
        """Execute firmware with the given hardware configuration.

        Returns a SimulationResult with all observations.
        """
        ...

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up temporary files and resources after a run."""
        ...

    def execute_test(
        self,
        firmware_path: str | Path,
        config: HardwareConfig,
    ) -> SimulationResult:
        """Convenience: prepare + execute + cleanup in one call."""
        self.prepare(firmware_path, config)
        try:
            result = self.execute(config)
        finally:
            self.cleanup()
        return result
