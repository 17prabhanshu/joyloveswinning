from ps3_agent.schemas import TestScenario, ExecutionResult, VerificationResult

def generate_markdown_report(run_id: str, results: list[dict]) -> str:
    md = [
        f"# Golden Run Report: {run_id}",
        "This report summarizes the autonomous red-team testing of the firmware.",
        ""
    ]
    
    total = len(results)
    passed = sum(1 for r in results if r.get("verification") and r["verification"]["status"] == "PASS")
    failed = sum(1 for r in results if r.get("verification") and r["verification"]["status"] == "FAIL")
    errors = total - passed - failed
    
    md.extend([
        "## Summary",
        f"- **Total Tests:** {total}",
        f"- **Passed:** {passed}",
        f"- **Failed:** {failed}",
        f"- **Errors:** {errors}",
        ""
    ])
    
    md.extend([
        "## Detected Failures & Root Causes",
        "The following failures were caught by the autonomous agent and analyzed for root causes.",
        ""
    ])
    
    failures = [r for r in results if r.get("verification") and r["verification"]["status"] == "FAIL"]
    
    if not failures:
        md.append("*No failures detected.*")
    else:
        for r in failures:
            test_id = r.get("test_id", "Unknown")
            scenario = r.get("scenario", {})
            diagnosis = r.get("diagnosis")
            
            reason = scenario.get("reason", "")
            target = scenario.get("target", "")
            
            # Clean up target temporary paths (e.g. tmpsfbsm3k0.c:75 -> fan_controller.c:75)
            import re
            target = re.sub(r'tmp[^:]+\.c:', 'fan_controller.c:', target)
            
            info_val = scenario.get("information_value", "")
            why = scenario.get("why_this_test_exists", "")
            
            md.append(f"### {test_id} - {target}")
            md.append(f"**Agent's Reasoning for this test:** {why} {info_val}")
            
            llm_analysis = r.get("llm_analysis")
            if llm_analysis:
                md.append(f"**Root Cause Diagnosis (LLM):** {llm_analysis}")
            elif diagnosis:
                likely_cause = diagnosis.get("likely_cause", diagnosis.get("cause_hypothesis", "No cause provided"))
                md.append(f"**Root Cause Diagnosis (Fallback):** {likely_cause}")
            else:
                md.append("**Root Cause Diagnosis:** Analysis pending/unavailable.")
            
            md.append("")
            
            md.append("")
    
    md.extend([
        "## Generated Test Cases (All)",
        "The complete list of test scenarios chosen by the agent's planner.",
        ""
    ])
    
    for r in results:
        test_id = r.get("test_id", "Unknown")
        scenario = r.get("scenario", {})
        status = r.get("verification", {}).get("status", "UNKNOWN")
        
        why = scenario.get("why_this_test_exists", "")
        target = scenario.get('target', 'N/A')
        
        # Clean up target temporary paths
        import re
        target = re.sub(r'tmp[^:]+\.c:', 'fan_controller.c:', target)
        
        md.append(f"#### {test_id} [{status}]")
        md.append(f"- **Target:** {target}")
        md.append(f"- **Reasoning:** {why}")
        
    return "\n".join(md)
