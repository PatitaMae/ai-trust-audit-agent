"""
agents/control_tester.py — NIST 800-53 Control Testing Agent
─────────────────────────────────────────────────────────────
Loads control catalog, assigns sub-scores, runs risk engine.
Deterministic only — no LLM calls. Audit reproducibility first.
"""

import json
from pathlib import Path

from audit_log.logger import AuditLogger
from scoring.risk_engine import RiskEngine
from models import ControlScore, MaturityScore


class ControlTesterAgent:
    def __init__(self, config: dict, logger: AuditLogger):
        self.config = config
        self.logger = logger
        self.engine = RiskEngine(
            likelihood_weight=config["scoring"]["weights"]["likelihood"],
            impact_weight=config["scoring"]["weights"]["impact"],
        )

    def run(self) -> list[ControlScore]:
        """Score all controls in the NIST 800-53 catalog."""
        self.logger.log("control_tester", "run_start", {})

        controls = self._load_control_catalog()
        scored = []

        for ctrl in controls:
            result = self.engine.calculate(
                ctrl["control_id"],
                ctrl.get("design_score", 2),
                ctrl.get("operating_score", 2),
                ctrl.get("evidence_score", 1),
            )
            scored.append(ControlScore(
                control_id=ctrl["control_id"],
                framework="nist_800_53",
                score=result["maturity"],
                design_effectiveness=ctrl.get("design_score", 2),
                operating_effectiveness=ctrl.get("operating_score", 2),
                evidence_quality=ctrl.get("evidence_score", 1),
                risk_score=result["risk_score"],
                notes=ctrl.get("notes"),
                evidence_refs=ctrl.get("evidence_refs", []),
            ))

        critical = [c for c in scored if c.risk_score >= 8.0]
        self.logger.log("control_tester", "run_complete", {
            "total_controls": len(scored),
            "critical": len(critical),
        })

        return scored

    def _load_control_catalog(self) -> list[dict]:
        catalog_path = Path("./frameworks/nist_800_53.json")
        if catalog_path.exists():
            return json.loads(catalog_path.read_text())
        return SIMULATED_CONTROLS


# ── Simulated control assessment data ────────────────────────────────────────
# Replace with your actual NIST 800-53 mappings JSON

SIMULATED_CONTROLS = [
    {"control_id": "AC-2",  "design_score": 3, "operating_score": 2, "evidence_score": 2,
     "notes": "Account management process exists but UAR cadence inconsistent",
     "evidence_refs": ["e007"]},
    {"control_id": "AC-3",  "design_score": 3, "operating_score": 3, "evidence_score": 3,
     "notes": "Role-based access enforced via Okta",
     "evidence_refs": ["e007"]},
    {"control_id": "AC-6",  "design_score": 2, "operating_score": 1, "evidence_score": 1,
     "notes": "Least privilege not consistently applied for contractors",
     "evidence_refs": []},
    {"control_id": "AU-2",  "design_score": 3, "operating_score": 3, "evidence_score": 2,
     "notes": "Audit events defined; log review cadence informal",
     "evidence_refs": []},
    {"control_id": "AU-9",  "design_score": 4, "operating_score": 4, "evidence_score": 4,
     "notes": "Audit log protection fully implemented",
     "evidence_refs": []},
    {"control_id": "CM-6",  "design_score": 2, "operating_score": 2, "evidence_score": 1,
     "notes": "Config baseline defined; drift detection missing",
     "evidence_refs": ["e009"]},
    {"control_id": "IR-4",  "design_score": 4, "operating_score": 3, "evidence_score": 3,
     "notes": "IRP documented and tabletop completed annually",
     "evidence_refs": ["e002"]},
    {"control_id": "IR-6",  "design_score": 3, "operating_score": 3, "evidence_score": 2,
     "notes": "Incident reporting process defined; evidence collection gaps",
     "evidence_refs": ["e002"]},
    {"control_id": "RA-3",  "design_score": 3, "operating_score": 3, "evidence_score": 3,
     "notes": "Risk assessment conducted annually",
     "evidence_refs": ["e008"]},
    {"control_id": "RA-5",  "design_score": 2, "operating_score": 1, "evidence_score": 1,
     "notes": "Vulnerability scanning ad hoc, not on schedule",
     "evidence_refs": []},
    {"control_id": "SC-8",  "design_score": 4, "operating_score": 4, "evidence_score": 3,
     "notes": "TLS enforced; certificate inventory partially documented",
     "evidence_refs": ["e010"]},
    {"control_id": "SC-28", "design_score": 4, "operating_score": 4, "evidence_score": 4,
     "notes": "Encryption at rest fully implemented and documented",
     "evidence_refs": ["e010"]},
]
