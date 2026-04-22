"""
agents/orchestrator.py — Central workflow router
─────────────────────────────────────────────────
Routes tasks between agents, validates outputs via schema,
manages pipeline state, and writes every action to the audit log.
"""

import yaml
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from audit_log.logger import AuditLogger
from models import AuditReport

console = Console()


class Orchestrator:
    def __init__(self, config_path: str = "./config/config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = AuditLogger(self.config["output"]["log_dir"])
        self.pipeline_state: dict = {}
        self.run_id = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    def _load_config(self, path: str) -> dict:
        cfg_file = Path(path)
        if not cfg_file.exists():
            raise FileNotFoundError(
                f"Config not found at {path}. "
                "Copy config/config.example.yaml → config/config.yaml and add your API key."
            )
        with open(cfg_file) as f:
            return yaml.safe_load(f)

    def run_full_audit(self) -> AuditReport:
        """Execute the full 4-agent pipeline in sequence."""
        console.print(Panel(
            f"[bold cyan]AI Trust & Audit Agent[/bold cyan]\n"
            f"Run ID: {self.run_id} | Org: {self.config['audit']['org_name']}",
            border_style="cyan"
        ))

        self.logger.log("orchestrator", "pipeline_start", {"run_id": self.run_id})

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # ── Agent 1: Control Tester ──────────────────────────────
            task = progress.add_task("[yellow]Running Control Tester...", total=None)
            from agents.control_tester import ControlTesterAgent
            ct = ControlTesterAgent(self.config, self.logger)
            control_results = ct.run()
            self.pipeline_state["control_results"] = control_results
            self._validate_output("control_tester", control_results)
            progress.update(task, description="[green]✓ Control Tester complete")

            # ── Agent 2: Evidence & UAR ──────────────────────────────
            task = progress.add_task("[yellow]Running Evidence & UAR Agent...", total=None)
            from agents.evidence_uar_agent import EvidenceUARAgent
            eur = EvidenceUARAgent(self.config, self.logger)
            uar_findings, evidence_inventory = eur.run()
            self.pipeline_state["uar_findings"] = uar_findings
            self.pipeline_state["evidence_inventory"] = evidence_inventory
            progress.update(task, description="[green]✓ Evidence & UAR complete")

            # ── Agent 3: Gap Analyzer ────────────────────────────────
            task = progress.add_task("[yellow]Running Gap Analyzer...", total=None)
            from agents.gap_analyzer import GapAnalyzerAgent
            ga = GapAnalyzerAgent(self.config, self.logger)
            gap_reports = ga.run(
                control_results=self.pipeline_state["control_results"],
                evidence_inventory=self.pipeline_state["evidence_inventory"],
            )
            self.pipeline_state["gap_reports"] = gap_reports
            progress.update(task, description="[green]✓ Gap Analyzer complete")

            # ── Agent 4: Report Drafter ──────────────────────────────
            task = progress.add_task("[yellow]Running Report Drafter...", total=None)
            from agents.report_drafter import ReportDrafterAgent
            rd = ReportDrafterAgent(self.config, self.logger)
            report = rd.run(
                gap_reports=self.pipeline_state["gap_reports"],
                uar_findings=self.pipeline_state["uar_findings"],
                evidence_inventory=self.pipeline_state["evidence_inventory"],
            )
            self.pipeline_state["report"] = report
            progress.update(task, description="[green]✓ Report Drafter complete")

        self.logger.log("orchestrator", "pipeline_complete", {
            "run_id": self.run_id,
            "maturity_score": report.overall_maturity_score,
            "critical_findings": report.critical_finding_count,
        })

        console.print(Panel(
            f"[bold green]Audit Complete[/bold green]\n"
            f"Overall Maturity: [cyan]{report.overall_maturity_score:.1f}/100[/cyan]\n"
            f"Critical Findings: [red]{report.critical_finding_count}[/red] | "
            f"High: [yellow]{report.high_finding_count}[/yellow]",
            border_style="green"
        ))

        return report

    def run_single_agent(self, agent_name: str):
        """Run a single agent independently for development/testing."""
        agents = {
            "control_tester":   self._run_control_tester,
            "evidence_uar":     self._run_evidence_uar,
            "gap_analyzer":     self._run_gap_analyzer,
            "report_drafter":   self._run_report_drafter,
        }
        if agent_name not in agents:
            raise ValueError(f"Unknown agent: {agent_name}. Choose from {list(agents.keys())}")
        return agents[agent_name]()

    def _validate_output(self, agent_name: str, output) -> bool:
        """Schema validation — catches malformed outputs before downstream agents consume them."""
        if output is None:
            self.logger.log("orchestrator", "validation_failed", {
                "agent": agent_name, "reason": "None output"
            }, severity="error")
            raise ValueError(f"{agent_name} returned None — pipeline halted")
        self.logger.log("orchestrator", "validation_passed", {"agent": agent_name})
        return True

    def verify_audit_log(self) -> bool:
        """Verify the audit log chain integrity."""
        valid = self.logger.verify_chain()
        status = "✓ intact" if valid else "✗ TAMPERED"
        console.print(f"Audit log chain: [{'green' if valid else 'red'}]{status}[/]")
        return valid

    # ── Single-agent runners (for --agent CLI flag) ──────────────────

    def _run_control_tester(self):
        from agents.control_tester import ControlTesterAgent
        return ControlTesterAgent(self.config, self.logger).run()

    def _run_evidence_uar(self):
        from agents.evidence_uar_agent import EvidenceUARAgent
        return EvidenceUARAgent(self.config, self.logger).run()

    def _run_gap_analyzer(self):
        from agents.gap_analyzer import GapAnalyzerAgent
        ct_results = self._run_control_tester()
        _, evidence = self._run_evidence_uar()
        return GapAnalyzerAgent(self.config, self.logger).run(ct_results, evidence)

    def _run_report_drafter(self):
        gap = self._run_gap_analyzer()
        _, uar = self._run_evidence_uar()
        _, evidence = self._run_evidence_uar()
        from agents.report_drafter import ReportDrafterAgent
        return ReportDrafterAgent(self.config, self.logger).run(gap, uar, evidence)
