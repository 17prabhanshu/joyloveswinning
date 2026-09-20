"""Simulator adapter package - abstracts firmware execution backends."""
from firmware_agent.simulator.base import SimulatorAdapter, SimulationResult, HardwareConfig
from firmware_agent.simulator.labwired import LabWiredAdapter

__all__ = ["SimulatorAdapter", "SimulationResult", "HardwareConfig", "LabWiredAdapter"]
