"""
agents/gap_analyzer.py — Multi-Framework Gap Analysis Agent
────────────────────────────────────────────────────────────
Layer 1: Ingests control scores + evidence coverage
Layer 2: Deterministic gap scoring via risk engine
Layer 3: LLM-generated remediation recommendations (Claude API)

Hybrid architecture: scoring is deterministic (auditable),
language is generative (efficient).
"""

import json
import anthropic
from pathlib import Path

from audit_log.logger import AuditLogger
from scoring.risk_engine import RiskEngine
from models import (
    GapFinding, FrameworkGapReport, EvidenceArtifact,
    ControlScore, MaturityScore
)


class GapAnalyzerAgent:
    def __init__(self, config: dict, logger: AuditLogger):
        self.config = config
        self.logger = logger
        self.engine = RiskEngine(
            likelihood_weight=config["scoring"]["weights"]["likelihood"],
            impact_weight=config["scoring"]["weights"]["impact"],
        )
        self.client = anthropic.Anthropic(api_key=config["anthropic"]["api_key"])
        self.model = config["anthropic"]["model"]

    def run(
        self,
        control_results: list[ControlScore],
        evidence_inventory: list[EvidenceArtifact],
    ) -> list[FrameworkGapReport]:
        """Analyze gaps across all configured frameworks."""
        self.logger.log("gap_analyzer", "run_start", {
            "frameworks": self.config["audit"]["frameworks"]
        })

        # Build evidence coverage map: control_id → list of artifact IDs
        evidence_map = self._build_evidence_map(evidence_inventory)

        reports = []
        for framework in self.config["audit"]["frameworks"]:
            report = self._analyze_framework(framework, control_results, evidence_map)
            reports.append(report)
            self.logger.log("gap_analyzer", "framework_complete", {
                "framework": framework,
                "maturity_score": report.maturity_score,
                "gaps": report.gaps,
                "critical_gaps": len(report.critical_gaps),
            })

        self.logger.log("gap_analyzer", "run_complete", {
            "frameworks_analyzed": len(reports)
        })
        return reports

    def _analyze_framework(
        self,
        framework: str,
        control_results: list[ControlScore],
        evidence_map: dict,
    ) -> FrameworkGapReport:
        """Score all controls for a given framework and build gap report."""
        catalog = self._load_framework_catalog(framework)
        gap_findings: list[GapFinding] = []

        scores_by_id = {c.control_id: c for c in control_results}

        compliant = partial = in_dev = gaps = 0

        for ctrl in catalog:
            cid = ctrl["control_id"]

            # Use existing control score if available, else default
            existing = scores_by_id.get(cid)
            if existing:
                d, o, e = (existing.design_effectiveness,
                           existing.operating_effectiveness,
                           existing.evidence_quality)
            else:
                # Adjust evidence score based on coverage
                has_evidence = cid in evidence_map
                d, o, e = 2, 2, (2 if has_evidence else 0)

            result = self.engine.calculate(cid, d, o, e)
            maturity = result["maturity"]

            # Tally counts
            if maturity == MaturityScore.OPTIMIZED:      compliant += 1
            elif maturity == MaturityScore.MANAGED:      partial += 1
            elif maturity == MaturityScore.IN_DEVELOPMENT: in_dev += 1
            else:                                         gaps += 1

            # Only call LLM for gaps (scores 0-2) to limit API cost
            if maturity.value <= 2:
                missing_evidence = ctrl.get("required_evidence", [])
                found_evidence = evidence_map.get(cid, [])
                missing = [e for e in missing_evidence if e not in found_evidence]

                remediation = self._get_remediation(
                    cid, ctrl["description"], framework, result["risk_score"], missing
                )

                gap_findings.append(GapFinding(
                    control_id=cid,
                    framework=framework,
                    description=ctrl["description"],
                    current_score=maturity,
                    risk_score=result["risk_score"],
                    risk_level=result["risk_level"],
                    remediation=remediation,
                    effort=self._estimate_effort(cid, maturity),
                    priority=self._priority_rank(result["risk_score"]),
                    evidence_missing=missing,
                ))

        # Sort gaps by risk score descending
        gap_findings.sort(key=lambda g: g.risk_score, reverse=True)

        total = len(catalog)
        maturity_score = round(
            ((compliant * 4 + partial * 3 + in_dev * 2) / (total * 4)) * 100, 1
        ) if total > 0 else 0.0

        return FrameworkGapReport(
            framework=framework,
            total_controls=total,
            compliant=compliant,
            partial=partial,
            in_development=in_dev,
            gaps=gaps,
            critical_gaps=[g for g in gap_findings if g.risk_level in ("critical", "high")],
            maturity_score=maturity_score,
        )

    def _get_remediation(
        self,
        control_id: str,
        description: str,
        framework: str,
        risk_score: float,
        missing_evidence: list[str],
    ) -> str:
        """Call Claude API to generate remediation language for a gap."""
        try:
            missing_str = (
                f"Missing evidence: {', '.join(missing_evidence)}" if missing_evidence
                else "No evidence artifacts on file."
            )
            prompt = (
                f"You are a senior GRC analyst writing remediation guidance for an audit report.\n\n"
                f"Framework: {framework.upper()}\n"
                f"Control: {control_id} — {description}\n"
                f"Risk Score: {risk_score}/10\n"
                f"{missing_str}\n\n"
                f"Write a concise (2-3 sentence) remediation recommendation. "
                f"Be specific, actionable, and reference the framework. "
                f"Do not use bullet points."
            )
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text.strip()
        except Exception as e:
            self.logger.log("gap_analyzer", "llm_error", {"control": control_id, "error": str(e)},
                            severity="error")
            return f"Manual review required for {control_id}. Implement control per {framework} guidance."

    def _build_evidence_map(self, evidence: list[EvidenceArtifact]) -> dict[str, list[str]]:
        """Map control IDs to evidence artifact IDs."""
        mapping: dict[str, list[str]] = {}
        for artifact in evidence:
            for framework_controls in artifact.framework_tags.values():
                for ctrl in framework_controls:
                    mapping.setdefault(ctrl, []).append(artifact.id)
        return mapping

    def _estimate_effort(self, control_id: str, maturity: MaturityScore) -> str:
        """Estimate remediation effort based on control type and maturity gap."""
        high_effort_controls = {"AC-2", "RA-5", "CM-6", "GOVERN-1.1", "MEASURE-2.5"}
        if control_id in high_effort_controls and maturity.value <= 1:
            return "High"
        if maturity.value == 0:
            return "High"
        if maturity.value == 1:
            return "Medium"
        return "Low"

    def _priority_rank(self, risk_score: float) -> int:
        if risk_score >= 8.0: return 1
        if risk_score >= 6.0: return 2
        if risk_score >= 4.0: return 3
        return 4

    def _load_framework_catalog(self, framework: str) -> list[dict]:
        catalog_path = Path(f"./frameworks/{framework}.json")
        if catalog_path.exists():
            return json.loads(catalog_path.read_text())
        return FRAMEWORK_CATALOGS.get(framework, [])


# ── Simulated framework catalogs ─────────────────────────────────────────────

FRAMEWORK_CATALOGS = {
    "nist_ai_rmf": [
        {"control_id": "GOVERN-1.1", "description": "Organizational AI risk policies and risk tolerance are documented",
         "required_evidence": ["ai_governance_policy"]},
        {"control_id": "GOVERN-1.2", "description": "AI risk management roles and responsibilities are assigned",
         "required_evidence": ["org_chart", "raci_matrix"]},
        {"control_id": "MAP-1.1",    "description": "AI system context and intended use cases are documented",
         "required_evidence": ["ai_system_card"]},
        {"control_id": "MAP-2.2",    "description": "AI risk categorization and impact assessments are completed",
         "required_evidence": ["risk_assessment"]},
        {"control_id": "MEASURE-2.5","description": "AI system performance is monitored post-deployment",
         "required_evidence": ["model_monitoring_runbook", "monitoring_dashboard"]},
        {"control_id": "MEASURE-2.6","description": "Bias and fairness metrics are tracked",
         "required_evidence": ["bias_evaluation_report"]},
        {"control_id": "MANAGE-1.3", "description": "AI risk response plans are documented and tested",
         "required_evidence": ["ai_incident_response_plan"]},
        {"control_id": "MANAGE-2.2", "description": "AI system decommission and rollback procedures exist",
         "required_evidence": ["decommission_runbook"]},
    ],
    "iso_42001": [
        {"control_id": "A.6.1", "description": "AI system design objectives are documented",
         "required_evidence": ["system_design_doc"]},
        {"control_id": "A.6.2", "description": "AI risk assessment methodology is defined",
         "required_evidence": ["risk_assessment"]},
        {"control_id": "A.9.1", "description": "AI system monitoring processes are established",
         "required_evidence": ["model_monitoring_runbook"]},
        {"control_id": "A.9.2", "description": "Feedback mechanisms for AI system improvement are in place",
         "required_evidence": ["feedback_process_doc"]},
    ],
    "soc2": [
        {"control_id": "CC6.1", "description": "Logical access controls are implemented",
         "required_evidence": ["access_control_matrix"]},
        {"control_id": "CC6.7", "description": "Data is encrypted in transit and at rest",
         "required_evidence": ["encryption_standards"]},
        {"control_id": "CC7.3", "description": "Security incidents are identified and responded to",
         "required_evidence": ["incident_response_plan"]},
        {"control_id": "CC8.1", "description": "Change management process controls are in place",
         "required_evidence": ["change_management_procedure"]},
        {"control_id": "CC9.2", "description": "Vendor and third-party risk is managed",
         "required_evidence": ["vendor_management_policy"]},
        {"control_id": "CC9.9", "description": "Acceptable use policies are documented and communicated",
         "required_evidence": ["acceptable_use_policy"]},
    ],
}
