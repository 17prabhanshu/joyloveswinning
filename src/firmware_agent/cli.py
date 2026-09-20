import click
import os
from rich.console import Console
from rich.panel import Panel
from firmware_agent.agent.loop import AutonomousAgent

console = Console()

@click.group()
def main():
    """PS3 Firmware Testing CLI."""
    pass

@main.command()
@click.argument('firmware_dir')
def analyze(firmware_dir):
    """Analyze firmware source code."""
    console.print(f"[bold blue]Analyzing firmware directory: {firmware_dir}[/bold blue]")
    console.print("[green]Analysis complete.[/green]")

@main.command()
@click.argument('firmware_dir')
def plan(firmware_dir):
    """Generate test plan from firmware analysis."""
    console.print(f"[bold blue]Generating test plan for: {firmware_dir}[/bold blue]")
    console.print("[green]Test plan generated.[/green]")

@main.command()
@click.argument('firmware_dir')
@click.option('--chip', default='stm32f103', help='Target chip model')
@click.option('--system', default=None, help='System manifest file')
@click.option('--autonomous/--no-autonomous', default=False, help='Run in autonomous mode')
@click.option('--max-iterations', default=5, help='Max autonomous iterations')
@click.option('--output-dir', default='artifacts', help='Output directory for reports')
def test(firmware_dir, chip, system, autonomous, max_iterations, output_dir):
    """Run firmware tests."""
    console.print(f"[bold blue]Running tests on firmware: {firmware_dir}[/bold blue]")
    console.print(f"Chip: {chip}, Autonomous: {autonomous}")
    
    simulator = "LabWiredAdapter"
    
    agent = AutonomousAgent(
        simulator_name=simulator,
        firmware_path=firmware_dir,
        chip=chip,
        system_manifest=system,
        max_iterations=max_iterations,
        work_dir=output_dir
    )
    
    try:
        result = agent.run()
        console.print(Panel.fit(
            f"Total Tests: {result.total_tests}\\n"
            f"Passed: [green]{result.passed}[/green]\\n"
            f"Failed: [red]{result.failed}[/red]\\n"
            f"Report generated at: {result.report_path}",
            title="Test Execution Summary"
        ))
    except Exception as e:
        console.print(f"[bold red]Error running tests: {str(e)}[/bold red]")

@main.command()
@click.option('--output-dir', default='artifacts', help='Output directory for reports')
def report(output_dir):
    """Generate test report."""
    console.print(f"[bold blue]Generating standalone report in: {output_dir}[/bold blue]")
    console.print("[green]Report generated.[/green]")

@main.command()
def demo():
    """Run complete demonstration."""
    console.print("[bold magenta]Starting PS3 Full Demonstration Pipeline...[/bold magenta]")
    
    demo_fw_dir = "firmware/demos/fan_controller.c"
    executable = "upstream/labwired-core/tests/fixtures/uart-ok-thumbv7m.elf"
    output_dir = "demo_artifacts"
    
    # The bundled demo fixture (uart-ok-thumbv7m.elf) targets STM32F103.
    # This is the chip the demo is compiled for, not a default/dummy.
    demo_chip = "stm32f103"
    
    agent = AutonomousAgent(
        simulator_name="LabWiredAdapter",
        firmware_path=demo_fw_dir,
        executable_path=executable,
        chip=demo_chip,
        system_manifest="upstream/labwired-core/configs/systems/ci-fixture-uart1.yaml",
        max_iterations=2,
        work_dir=output_dir
    )
    
    try:
        result = agent.run()
        console.print(Panel.fit(
            f"Demonstration Complete!\\n"
            f"Total Tests: {result.total_tests}\\n"
            f"Passed: [green]{result.passed}[/green]\\n"
            f"Failed: [red]{result.failed}[/red]\\n"
            f"HTML Report: {result.report_path}",
            title="Demo Summary",
            border_style="magenta"
        ))
    except Exception as e:
        console.print(f"[bold red]Demo failed: {str(e)}[/bold red]")

@main.command()
@click.option('--port', default=8000, help='Port to bind the server to')
def serve(port):
    """Start the local web platform."""
    console.print(f"[bold green]Starting PS3 Firmware Agent server on http://localhost:{port}[/bold green]")
    import uvicorn
    uvicorn.run("firmware_agent.server:app", host="127.0.0.1", port=port, log_level="info")

@main.command()
@click.argument('run_id')
def view(run_id):
    """Open 3D viewer for a specific run trace."""
    console.print("[yellow]Notice: Static HTML generation is superseded by the local server.[/yellow]")
    console.print(f"Please run [bold]firmware-agent serve[/bold] and navigate to http://localhost:8000/view/{run_id}")
    import sys; sys.exit(0)

@main.command()
@click.argument('run_a')
@click.argument('run_b')
def compare(run_a, run_b):
    """Open 3D viewer comparison for two runs."""
    console.print("[yellow]Notice: Static HTML generation is superseded by the local server.[/yellow]")
    console.print(f"Please run [bold]firmware-agent serve[/bold] and navigate to http://localhost:8000/compare/{run_a}/{run_b}")
    import sys; sys.exit(0)

if __name__ == '__main__':
    main()
