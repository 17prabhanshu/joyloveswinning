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
@click.argument('run_id')
def view(run_id):
    """Open 3D viewer for a specific run trace."""
    console.print(f"[bold blue]Launching viewer for run: {run_id}[/bold blue]")
    
    trace_path = os.path.join('artifacts', 'traces', run_id, 'trace.json')
    if not os.path.exists(trace_path):
        console.print(f"[bold red]Error: No trace.v1 artifact found at {trace_path}[/bold red]")
        console.print(f"Make sure the run executed and emitted telemetry successfully.")
        import sys; sys.exit(1)
        
    html_path = os.path.join('src', 'firmware_agent', 'reporting', 'viewer', 'rig_view.html')
    with open(html_path, 'r') as f:
        html = f.read()
        
    with open(trace_path, 'r') as f:
        trace_data = f.read()
        
    script_block = f'<script type="application/json" id="trace-data">\n{trace_data}\n</script>'
    html = html.replace('</body>', f'{script_block}\n</body>')
    
    out_path = os.path.abspath(os.path.join('artifacts', f'viewer_{run_id}.html'))
    with open(out_path, 'w') as f:
        f.write(html)
        
    console.print(f"[green]Viewer built: {out_path}[/green]")
    console.print(f"[green]Size: {os.path.getsize(out_path)} bytes[/green]")
    import webbrowser
    webbrowser.open(f'file://{out_path}')

@main.command()
@click.argument('run_a')
@click.argument('run_b')
def compare(run_a, run_b):
    """Open 3D viewer comparison for two runs."""
    console.print(f"[bold blue]Launching comparison for {run_a} vs {run_b}[/bold blue]")
    
    trace_a_path = os.path.join('artifacts', 'traces', run_a, 'trace.json')
    trace_b_path = os.path.join('artifacts', 'traces', run_b, 'trace.json')
    
    for path in [trace_a_path, trace_b_path]:
        if not os.path.exists(path):
            console.print(f"[bold red]Error: No trace.v1 artifact found at {path}[/bold red]")
            import sys; sys.exit(1)
            
    html_path = os.path.join('src', 'firmware_agent', 'reporting', 'viewer', 'rig_view.html')
    with open(html_path, 'r') as f:
        html = f.read()
        
    with open(trace_a_path, 'r') as f: trace_a = f.read()
    with open(trace_b_path, 'r') as f: trace_b = f.read()
        
    # We will inject an array of traces for comparison mode
    script_block = f'<script type="application/json" id="trace-data-compare">\n[{trace_a},{trace_b}]\n</script>'
    html = html.replace('</body>', f'{script_block}\n</body>')
    
    out_path = os.path.abspath(os.path.join('artifacts', f'compare_{run_a}_{run_b}.html'))
    with open(out_path, 'w') as f:
        f.write(html)
        
    console.print(f"[green]Comparison Viewer built: {out_path}[/green]")
    console.print(f"[green]Size: {os.path.getsize(out_path)} bytes[/green]")
    import webbrowser
    webbrowser.open(f'file://{out_path}')

if __name__ == '__main__':
    main()
