"""
main.py — ATAA CLI Entry Point
Usage:
  python main.py                          # full audit pipeline
  python main.py --agent gap_analyzer     # single agent
  python main.py --verify-log             # check audit log integrity
  python main.py --questionnaire          # run sample questionnaire
"""

import typer
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="AI Trust & Audit Agent (ATAA)")
console = Console()


@app.command()
def main(
    mode: str = typer.Option("full", "--mode", "-m",
                              help="Run mode: full | single"),
    agent: str = typer.Option(None, "--agent", "-a",
                               help="Agent: control_tester | evidence_uar | gap_analyzer | report_drafter"),
    verify_log: bool = typer.Option(False, "--verify-log",
                                     help="Verify audit log chain integrity"),
    questionnaire: bool = typer.Option(False, "--questionnaire",
                                        help="Run sample customer questionnaire"),
    config: str = typer.Option("./config/config.yaml", "--config", "-c",
                                 help="Path to config file"),
):
    from agents.orchestrator import Orchestrator
    orch = Orchestrator(config_path=config)

    if verify_log:
        orch.verify_audit_log()
        return

    if questionnaire:
        _run_sample_questionnaire(orch, config)
        return

    if agent:
        console.print(f"[cyan]Running single agent: {agent}[/cyan]")
        result = orch.run_single_agent(agent)
        console.print(f"[green]✓ Done[/green] — {type(result).__name__}")
        return

    # Full pipeline
    report = orch.run_full_audit()
    _print_summary_table(report)


def _print_summary_table(report):
    """Pretty-print framework maturity scores."""
    table = Table(title="Framework Maturity Scores", border_style="cyan")
    table.add_column("Framework", style="bold")
    table.add_column("Maturity", justify="right")
    table.add_column("Controls", justify="right")
    table.add_column("Gaps", justify="right", style="red")
    table.add_column("Critical", justify="right", style="bold red")

    for r in report.gap_reports:
        table.add_row(
            r.framework.upper(),
            f"{r.maturity_score:.1f}/100",
            str(r.total_controls),
            str(r.gaps),
            str(len(r.critical_gaps)),
        )

    console.print(table)
    console.print(f"\n[bold]Overall Maturity:[/bold] {report.overall_maturity_score:.1f}/100")
    console.print(f"[bold]Recommendations:[/bold]")
    for i, rec in enumerate(report.recommendations, 1):
        console.print(f"  {i}. {rec}")


def _run_sample_questionnaire(orch, config_path):
    """Run the report drafter's questionnaire responder with sample questions."""
    import yaml
    from pathlib import Path
    from agents.report_drafter import ReportDrafterAgent
    from agents.evidence_uar_agent import EvidenceUARAgent
    from audit_log.logger import AuditLogger

    config = yaml.safe_load(Path(config_path).read_text())
    logger = AuditLogger(config["output"]["log_dir"])

    _, evidence = EvidenceUARAgent(config, logger).run()

    questions = [
        "Does your organization have a documented incident response plan tested annually?",
        "How do you manage and review third-party vendor security risks?",
        "What controls do you have in place for AI system governance and oversight?",
    ]

    drafter = ReportDrafterAgent(config, logger)
    responses = drafter.answer_questionnaire(questions, evidence)

    console.print("\n[bold cyan]Customer Security Questionnaire Responses[/bold cyan]\n")
    for r in responses:
        flag = "[red]⚠ HUMAN REVIEW REQUIRED[/red]" if r.human_review_required else "[green]✓ Ready[/green]"
        console.print(f"[bold]Q:[/bold] {r.question}")
        console.print(f"[bold]A:[/bold] {r.answer}")
        console.print(f"[bold]Confidence:[/bold] {r.confidence} | {flag}")
        console.print(f"[bold]Sources:[/bold] {', '.join(r.sources) or 'None found'}")
        console.print(f"[bold]Framework refs:[/bold] {', '.join(r.framework_refs) or 'None'}")
        console.print("─" * 60)


if __name__ == "__main__":
    app()
