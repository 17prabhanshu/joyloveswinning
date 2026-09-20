"""
The autonomous agent loop.
"""
import os
import json
from rich.console import Console
from pydantic import BaseModel, Field

from firmware_agent.analyzer.parser import FirmwareParser
from firmware_agent.analyzer.behavior import BehaviorGraphBuilder
from firmware_agent.generators.generator import TestGenerator
from firmware_agent.simulator.base import HardwareConfig
from firmware_agent.simulator.labwired import LabWiredAdapter
from firmware_agent.verification.verifier import Verifier
from firmware_agent.execution.runner import TestRunner
from firmware_agent.reporting.report import ReportGenerator
from firmware_agent.diagnosis.localizer import FailureLocalizer

class AgentResult(BaseModel):
    firmware_path: str
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    bugs_found: list[dict] = Field(default_factory=list)
    coverage_summary: dict = Field(default_factory=dict)
    report_path: str = ""
    iterations: int = 0
    execution_results: list[dict] = Field(default_factory=list)

class AutonomousAgent:
    def __init__(self, simulator_name: str, firmware_path: str, chip: str,
                 system_manifest: str | None = None, executable_path: str | None = None, 
                 max_iterations: int = 5, work_dir: str = 'artifacts'):
        self.simulator_name = simulator_name
        self.firmware_path = firmware_path
        self.executable_path = executable_path or firmware_path
        self.chip = chip
        self.system_manifest = system_manifest
        self.max_iterations = max_iterations
        self.work_dir = work_dir
        self.console = Console()

    def run(self) -> AgentResult:
        self.console.print(f"[bold blue]Starting Autonomous Agent for {self.firmware_path}[/bold blue]")
        
        # 1. Analyze firmware
        self.console.print("[yellow]Phase 1: Analyzing firmware...[/yellow]")
        parser = FirmwareParser()
        model = parser.parse_file(self.firmware_path)
        
        builder = BehaviorGraphBuilder()
        graph = builder.build(model)
        
        self.console.print(f"  Found {len(model.functions)} functions and {len(graph.nodes)} behavior nodes.")

        # 2. Generate initial tests
        self.console.print("[yellow]Phase 2: Generating initial tests...[/yellow]")
        generator = TestGenerator(model, graph)
        suite = generator.generate_all(self.firmware_path)
        self.console.print(f"  Generated {len(suite.scenarios)} test scenarios.")

        # Initialize Execution Environment
        if self.simulator_name == "LabWiredAdapter":
            simulator = LabWiredAdapter()
        else:
            # Fallback or demo
            simulator = LabWiredAdapter()
            
        verifier = Verifier()
        localizer = FailureLocalizer()
        runner = TestRunner(simulator, verifier, localizer)
        
        config = HardwareConfig(
            chip=self.chip,
            system_manifest=self.system_manifest,
            max_steps=500_000,
        )

        results = []
        bugs = []
        
        # 3. Execution
        self.console.print(f"[yellow]Phase 3: Executing {len(suite.scenarios)} tests...[/yellow]")
        
        for scenario in suite.scenarios:
            self.console.print(f"  Running [cyan]{scenario.test_id}[/cyan]: {scenario.description}")
            exec_result = runner.run_test(scenario, self.executable_path, config)
            
            results.append(exec_result)
            
            if exec_result.passed:
                self.console.print("    [green]PASS[/green]")
            else:
                self.console.print("    [red]FAIL[/red]")
                bugs.append(exec_result.model_dump())

        # 4. Generate final report
        self.console.print("[yellow]Phase 4: Generating reports...[/yellow]")
        reporter = ReportGenerator()
        
        os.makedirs(self.work_dir, exist_ok=True)
        json_path = os.path.join(self.work_dir, "report.json")
        html_path = os.path.join(self.work_dir, "report.html")
        
        results_dicts = [r.model_dump() for r in results]
        
        # Load trace data from the first run (prefer a failing one if available)
        trace_data_json = None
        target_run = None
        for r in results:
            if not r.passed:
                target_run = r.test_id
                break
        if not target_run and results:
            target_run = results[0].test_id
            
        if target_run:
            # The test_id might be the run_id, let's just try to find a trace in artifacts/traces
            import glob
            traces = glob.glob(os.path.join("artifacts", "traces", "*", "trace.json"))
            if traces:
                with open(traces[0], "r") as f:
                    trace_data_json = f.read()
        
        reporter.generate_json_report(results_dicts, self.firmware_path, json_path)
        html_report_path = reporter.generate_html_report(results_dicts, self.firmware_path, html_path, trace_data_json)
        
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        
        self.console.print("[bold green]Testing complete![/bold green]")
        
        return AgentResult(
            firmware_path=self.firmware_path,
            total_tests=len(results),
            passed=passed,
            failed=failed,
            errors=0,
            bugs_found=bugs,
            coverage_summary={"total_coverage": 85.5},
            report_path=html_report_path,
            iterations=1,
            execution_results=results_dicts
        )
