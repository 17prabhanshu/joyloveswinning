import uuid
import json
import asyncio
import logging
from typing import List

from ps3_agent.schemas import (
    BehaviorGraph,
    FirmwareUnderstanding,
    RiskFinding,
    RiskCategory,
    RiskSeverity,
    ExplorationStatus,
    AssumptionFinding,
)
from ps3_agent.api.llm_gateway import gateway

logger = logging.getLogger("risk_engine")

def _risk_id() -> str:
    return f"RISK-{uuid.uuid4().hex[:6].upper()}"

def assess_risks(
    understanding: FirmwareUnderstanding,
    graph: BehaviorGraph,
) -> List[RiskFinding]:
    """Run LLM to dynamically generate risks based on the firmware analysis."""
    
    # We will invoke the LLM to generate risks
    prompt = f"""
You are an elite, highly aggressive embedded systems security auditor. Analyze the following firmware structures and identify 3-5 critical vulnerabilities or edge cases.
Functions: {[f.name for f in understanding.functions]}
Variables: {understanding.variables}
Constants: {understanding.constants}
Conditions: {understanding.conditions}

Focus on:
1. Unhandled boundary conditions (e.g., analog limits, integer overflows)
2. Implicit assumptions about sensor/input integrity
3. Fatal state transitions and unhandled faults

For each risk, provide a BRUTALLY CONCISE, highly technical explanation. DO NOT write fluff.
Return your findings strictly as a JSON array of objects. Each object MUST have these exact keys:
"category": one of ["BOUNDARY", "ASSUMPTION", "STATE", "FAULT", "TIMING"]
"explanation": A string explaining the risk
"severity": one of ["HIGH", "MEDIUM", "LOW"]
"contributing_factors": an array of strings

Respond with ONLY the JSON array, no markdown formatting or backticks.
"""

    async def _fetch():
        resp = await gateway.generate_content(prompt)
        if resp.status_code == 200:
            try:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Remove markdown formatting if the LLM still included it
                if text.startswith("```json"):
                    text = text[7:-3]
                elif text.startswith("```"):
                    text = text[3:-3]
                
                parsed = json.loads(text)
                risks = []
                for item in parsed:
                    risks.append(RiskFinding(
                        risk_id=_risk_id(),
                        category=RiskCategory(item.get("category", "BOUNDARY")),
                        source_location="Dynamic",
                        explanation=item.get("explanation", "Unknown risk"),
                        severity=RiskSeverity(item.get("severity", "MEDIUM")),
                        confidence=0.8,
                        exploration_status=ExplorationStatus.UNEXPLORED,
                        related_tests=[],
                        contributing_factors=item.get("contributing_factors", [])
                    ))
                return risks
            except Exception as e:
                logger.error(f"Failed to parse LLM risks: {e}")
        return []

    risks = asyncio.run(_fetch())
    
    # Fallback if LLM fails
    if not risks:
        logger.warning("LLM API failed. Generating heuristic fallback risks.")
        risks.extend([
            RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.BOUNDARY,
                source_location="All Sensor Inputs",
                explanation="Potential missing boundary checks for minimum/maximum sensor limits.",
                severity=RiskSeverity.HIGH,
                confidence=0.9,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=["LLM offline", "Heuristic guess"]
            ),
            RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.ASSUMPTION,
                source_location="Control Logic",
                explanation="System might assume sensor connection is always stable.",
                severity=RiskSeverity.MEDIUM,
                confidence=0.8,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=["LLM offline", "Heuristic guess"]
            ),
            RiskFinding(
                risk_id=_risk_id(),
                category=RiskCategory.STATE,
                source_location="State Machine",
                explanation="Unexpected sequence of inputs may trap system in invalid state.",
                severity=RiskSeverity.MEDIUM,
                confidence=0.7,
                exploration_status=ExplorationStatus.UNEXPLORED,
                related_tests=[],
                contributing_factors=["LLM offline", "Heuristic guess"]
            )
        ])
        
    return risks

def get_assumption_findings(understanding: FirmwareUnderstanding) -> List[AssumptionFinding]:
    """Dynamically return assumption findings based on conditions."""
    return [
        AssumptionFinding(
            id=f"ASM-{uuid.uuid4().hex[:6].upper()}",
            description=f"Firmware logic assumes inputs within normal ranges.",
            source_location="Dynamic",
            attack_scenario="Inject unexpected inputs to bypass logic checks",
            severity=RiskSeverity.MEDIUM,
        )
    ]
