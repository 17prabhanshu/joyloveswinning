"""
Risk Engine — Identifies risky firmware behaviors through systematic hunting.

Runs specialized hunters (boundary, assumption, state, fault, timing)
and aggregates their findings into a unified risk map.
"""
from __future__ import annotations

import re
import uuid
from typing import Any

from ps3_agent.schemas import (
    AssumptionFinding,
    BehaviorGraph,
    FirmwareUnderstanding,
    RiskCategory,
    RiskFinding,
    RiskSeverity,
    ExplorationStatus,
)


def _risk_id() -> str:
    return f"RISK-{uuid.uuid4().hex[:6].upper()}"


def hunt_boundaries(understanding: FirmwareUnderstanding) -> list[RiskFinding]:
    """Find boundary conditions that control hardware outputs."""
    risks: list[RiskFinding] = []
    
    for func in understanding.functions:
        for cond in func.conditions:
            # Look for numeric comparisons
            match = re.search(r"(\w+)\s*(>|<|>=|<=|==|!=)\s*(\w+)", cond)
            if not match:
                continue
            
            var_name = match.group(1)
            operator = match.group(2)
            threshold = match.group(3)
            
            # Resolve constant value
            resolved_value = understanding.constants.get(threshold, threshold)
            
            # Higher severity if function controls hardware
            has_hw = len(func.hw_interactions) > 0
            severity = RiskSeverity.HIGH if has_hw else RiskSeverity.MEDIUM
            
            factors = [
                f"Condition: {cond}",
                f"Operator: {operator}",
                f"Threshold: {threshold} = {resolved_value}",
            ]
            if has_hw:
                factors.append(f"Controls hardware: {', '.join(func.hw_interactions)}")
            if operator == ">" and has_hw:
                factors.append("Uses > instead of >= — off-by-one risk at exact boundary")
            
            risks.append(RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.BOUNDARY,
                source_location=f"{func.file}:{func.line} in {func.name}()",
                explanation=f"Threshold `{cond}` in {func.name}() controls hardware output. "
                            f"Boundary value {resolved_value} may exhibit off-by-one behavior.",
                severity=severity,
                confidence=0.9 if has_hw else 0.6,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=factors,
            ))
    
    return risks


def hunt_assumptions(understanding: FirmwareUnderstanding) -> list[RiskFinding]:
    """Find implicit assumptions in the firmware."""
    risks: list[RiskFinding] = []
    
    # Check for sensor reads without error checking
    sensor_funcs = [f for f in understanding.functions if "read" in f.name.lower() or "sensor" in f.name.lower()]
    control_funcs = [f for f in understanding.functions if "control" in f.name.lower() or "fan" in f.name.lower()]
    
    for ctrl in control_funcs:
        # Check if control function validates sensor input
        has_disconnect_check = any("DISCONNECT" in c or "-999" in c or "error" in c.lower() for c in ctrl.conditions)
        has_range_check = any("SENSOR_MAX" in c or "valid" in c.lower() for c in ctrl.conditions)
        
        if not has_disconnect_check:
            risks.append(RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.ASSUMPTION,
                source_location=f"{ctrl.file}:{ctrl.line} in {ctrl.name}()",
                explanation=f"Function {ctrl.name}() assumes sensor data is always valid. "
                            f"No check for SENSOR_DISCONNECTED (-999). If sensor fails, "
                            f"firmware may interpret -999 as a valid cold temperature.",
                severity=RiskSeverity.HIGH,
                confidence=0.95,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=[
                    "No disconnect guard in control function",
                    "Sensor read can return error codes",
                    "Hardware output depends on unchecked input",
                ],
            ))
        
        if not has_range_check:
            risks.append(RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.ASSUMPTION,
                source_location=f"{ctrl.file}:{ctrl.line} in {ctrl.name}()",
                explanation=f"Function {ctrl.name}() has no range validation. "
                            f"Out-of-range values (e.g. 5000°C) are accepted without clamping.",
                severity=RiskSeverity.MEDIUM,
                confidence=0.85,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=[
                    "No upper/lower bound check on sensor value",
                    "Extreme values may cause undefined behavior",
                ],
            ))
    
    return risks


def hunt_states(understanding: FirmwareUnderstanding) -> list[RiskFinding]:
    """Find risky state transitions."""
    risks: list[RiskFinding] = []
    
    recovery_funcs = [f for f in understanding.functions if "recover" in f.name.lower()]
    for func in recovery_funcs:
        has_validation = any("valid" in c.lower() or "check" in c.lower() for c in func.conditions)
        if not has_validation:
            risks.append(RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.STATE,
                source_location=f"{func.file}:{func.line} in {func.name}()",
                explanation=f"Recovery function {func.name}() does not validate first reading "
                            f"after sensor reconnection. Blindly trusts potentially stale data.",
                severity=RiskSeverity.MEDIUM,
                confidence=0.8,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=[
                    "No first-reading validation after disconnect",
                    "Direct transition from ERROR to NORMAL",
                    "Recovery may use corrupted sensor data",
                ],
            ))
    
    # Check for state variables that can be modified by multiple functions
    if len(understanding.state_variables) > 0:
        risks.append(RiskFinding(
            risk_id=_risk_id(),
            category=RiskCategory.STATE,
            source_location=None,
            explanation=f"Found {len(understanding.state_variables)} state variables: "
                        f"{', '.join(understanding.state_variables[:5])}. "
                        f"State transitions may have untested sequences.",
            severity=RiskSeverity.LOW,
            confidence=0.5,
            exploration_status=ExplorationStatus.UNEXPLORED,
            related_tests=[],
            contributing_factors=[
                f"{len(understanding.state_variables)} mutable state variables",
                "Potential for invalid state combinations",
            ],
        ))
    
    return risks


def hunt_faults(understanding: FirmwareUnderstanding) -> list[RiskFinding]:
    """Find missing fault handling."""
    risks: list[RiskFinding] = []
    
    sensor_funcs = [f for f in understanding.functions if "read" in f.name.lower()]
    for func in sensor_funcs:
        risks.append(RiskFinding(
            risk_id=_risk_id(),
            category=RiskCategory.FAULT,
            source_location=f"{func.file}:{func.line} in {func.name}()",
            explanation=f"Sensor function {func.name}() can return error values. "
                        f"Callers must handle disconnect, timeout, and invalid readings.",
            severity=RiskSeverity.HIGH,
            confidence=0.85,
            exploration_status=ExplorationStatus.UNEXPLORED,
            related_tests=[],
            contributing_factors=[
                "Sensor can physically disconnect",
                "ADC can return out-of-range values",
                "Error propagation may be incomplete",
            ],
        ))
    
    return risks


def hunt_timing(understanding: FirmwareUnderstanding) -> list[RiskFinding]:
    """Find timing-related risks."""
    risks: list[RiskFinding] = []
    
    # Look for functions that write GPIO without delays
    gpio_writers = [f for f in understanding.functions if "GPIO_Write" in str(f.hw_interactions)]
    for func in gpio_writers:
        if "delay" not in " ".join(func.conditions).lower():
            risks.append(RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.TIMING,
                source_location=f"{func.file}:{func.line} in {func.name}()",
                explanation=f"Function {func.name}() writes GPIO without debounce delay. "
                            f"Rapid state transitions on inductive loads (motors) can cause "
                            f"back-EMF spikes damaging the MCU.",
                severity=RiskSeverity.MEDIUM,
                confidence=0.75,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=[
                    "No delay between GPIO state changes",
                    "Inductive load (fan motor) on GPIO",
                    "Rapid HIGH→LOW→HIGH transition risk",
                ],
            ))
            break  # Only report once
    
    return risks


def assess_risks(
    understanding: FirmwareUnderstanding,
    graph: BehaviorGraph,
) -> list[RiskFinding]:
    """Run all hunters and aggregate risk findings."""
    risks: list[RiskFinding] = []
    risks.extend(hunt_boundaries(understanding))
    risks.extend(hunt_assumptions(understanding))
    risks.extend(hunt_states(understanding))
    risks.extend(hunt_faults(understanding))
    risks.extend(hunt_timing(understanding))
    return risks


def get_assumption_findings(understanding: FirmwareUnderstanding) -> list[AssumptionFinding]:
    """Return structured assumption findings for the UI."""
    findings: list[AssumptionFinding] = []
    
    control_funcs = [f for f in understanding.functions if "control" in f.name.lower()]
    for ctrl in control_funcs:
        findings.append(AssumptionFinding(
            id=f"ASM-{uuid.uuid4().hex[:6].upper()}",
            description=f"Firmware assumes sensor reading is always valid before "
                        f"applying control logic in {ctrl.name}().",
            source_location=f"{ctrl.file}:{ctrl.line}",
            attack_scenario="Disconnect sensor to produce -999 reading during high-temp event",
            severity=RiskSeverity.HIGH,
        ))
    
    return findings
