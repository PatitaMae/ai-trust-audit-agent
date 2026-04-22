"""
agents/evidence_uar_agent.py — Evidence Collection + User Access Review
────────────────────────────────────────────────────────────────────────
Runs deterministic UAR rules against simulated user data.
Tags evidence artifacts against framework control catalogs.
No LLM calls — pure rule-based logic for audit reproducibility.
"""

import json
from datetime import datetime, date
from pathlib import Path

from audit_log.logger import AuditLogger
from models import UserRecord, UARFinding, EvidenceArtifact


# ── UAR Rule Definitions ─────────────────────────────────────────────────────
# Each rule: (label, severity, check_fn, recommended_action, control_ref)

UAR_RULES = [
    {
        "rule_id":   "UAR-001",
        "label":     "Terminated user with active system access",
        "severity":  "critical",
        "control":   "AC-2",
        "action":    "Immediately revoke all system access. Escalate to IT and HR.",
        "check":     lambda u: u.employment_status == "terminated" and len(u.systems) > 0,
    },
    {
        "rule_id":   "UAR-002",
        "label":     "Contractor with production database access",
        "severity":  "high",
        "control":   "AC-6",
        "action":    "Review business justification. Apply least-privilege. Add MFA.",
        "check":     lambda u: u.employment_status == "contractor" and
                               any("prod" in s.lower() or "db" in s.lower() for s in u.systems),
    },
    {
        "rule_id":   "UAR-003",
        "label":     "Manager review overdue (90+ days)",
        "severity":  "medium",
        "control":   "AC-2",
        "action":    "Send reminder to manager. Suspend access if no response in 14 days.",
        "check":     lambda u: u.manager_review == "pending",
    },
    {
        "rule_id":   "UAR-004",
        "label":     "Dormant account (180+ days inactive)",
        "severity":  "low",
        "control":   "AC-2",
        "action":    "Disable account pending confirmation from manager.",
        "check":     lambda u: u.last_access is not None and
                               _days_since(u.last_access) > 180,
    },
    {
        "rule_id":   "UAR-005",
        "label":     "No manager review on record",
        "severity":  "medium",
        "control":   "AC-2",
        "action":    "Initiate manager review. Document outcome in GRC platform.",
        "check":     lambda u: u.manager_review is None,
    },
]


def _days_since(date_str: str) -> int:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return (date.today() - d).days
    except Exception:
        return 0


# ── Evidence Framework Tagging Map ───────────────────────────────────────────
# Maps filename patterns → framework control references

EVIDENCE_TAG_MAP = {
    "acceptable_use":      {"nist_800_53": ["AC-1"], "soc2": ["CC9.9"], "iso_27001": ["A.8.1"]},
    "incident_response":   {"nist_800_53": ["IR-4", "IR-6"], "soc2": ["CC7.3"], "iso_27001": ["A.16.1"]},
    "access_control":      {"nist_800_53": ["AC-2", "AC-3"], "soc2": ["CC6.1"], "iso_42001": ["A.6.1"]},
    "risk_assessment":     {"nist_800_53": ["RA-3", "RA-5"], "nist_ai_rmf": ["MAP-1.1"], "iso_42001": ["A.6.2"]},
    "security_awareness":  {"nist_800_53": ["AT-2"], "soc2": ["CC1.4"], "iso_27001": ["A.7.2"]},
    "vendor_management":   {"nist_800_53": ["SA-9"], "soc2": ["CC9.2"], "iso_27001": ["A.15.1"]},
    "ai_governance":       {"nist_ai_rmf": ["GOVERN-1.1", "GOVERN-1.2"], "iso_42001": ["A.9.1"]},
    "model_monitoring":    {"nist_ai_rmf": ["MEASURE-2.5", "MEASURE-2.6"], "iso_42001": ["A.9.2"]},
    "change_management":   {"nist_800_53": ["CM-3", "CM-6"], "soc2": ["CC8.1"]},
    "encryption":          {"nist_800_53": ["SC-8", "SC-28"], "soc2": ["CC6.7"]},
}

REVIEW_OVERDUE_DAYS = 365   # flag evidence not reviewed in 12+ months


class EvidenceUARAgent:
    def __init__(self, config: dict, logger: AuditLogger):
        self.config = config
        self.logger = logger
        self.data_dir = Path("./data")

    def run(self) -> tuple[list[UARFinding], list[EvidenceArtifact]]:
        """Main entry point — returns (uar_findings, evidence_inventory)."""
        self.logger.log("evidence_uar_agent", "run_start", {})

        uar_findings = self._run_uar()
        evidence_inventory = self._collect_evidence()

        self.logger.log("evidence_uar_agent", "run_complete", {
            "uar_findings": len(uar_findings),
            "evidence_artifacts": len(evidence_inventory),
            "critical_uar": sum(1 for f in uar_findings if f.severity == "critical"),
        })

        return uar_findings, evidence_inventory

    # ── UAR ──────────────────────────────────────────────────────────────────

    def _run_uar(self) -> list[UARFinding]:
        users = self._load_users()
        findings: list[UARFinding] = []

        for user_data in users:
            user = UserRecord(**user_data)
            for rule in UAR_RULES:
                try:
                    if rule["check"](user):
                        findings.append(UARFinding(
                            user_id=user.id,
                            user_name=user.name,
                            severity=rule["severity"],
                            rule_triggered=rule["rule_id"],
                            description=rule["label"],
                            systems_affected=user.systems,
                            recommended_action=rule["action"],
                            control_ref=rule["control"],
                        ))
                        self.logger.log("evidence_uar_agent", "uar_finding", {
                            "rule": rule["rule_id"],
                            "user": user.name,
                            "severity": rule["severity"],
                        }, severity=rule["severity"])
                except Exception:
                    pass  # skip rule if data missing

        return findings

    # ── Evidence Collection ───────────────────────────────────────────────────

    def _collect_evidence(self) -> list[EvidenceArtifact]:
        evidence_list = self._load_evidence_manifest()
        artifacts: list[EvidenceArtifact] = []

        for item in evidence_list:
            tags = self._tag_artifact(item["filename"])
            overdue = False
            if item.get("last_reviewed"):
                overdue = _days_since(item["last_reviewed"]) > REVIEW_OVERDUE_DAYS

            artifact = EvidenceArtifact(
                id=item["id"],
                filename=item["filename"],
                artifact_type=item["type"],
                framework_tags=tags,
                last_reviewed=item.get("last_reviewed"),
                review_overdue=overdue,
                notes=item.get("notes"),
            )
            artifacts.append(artifact)

            if overdue:
                self.logger.log("evidence_uar_agent", "evidence_overdue", {
                    "artifact": item["filename"],
                    "last_reviewed": item.get("last_reviewed"),
                }, severity="medium")

        return artifacts

    def _tag_artifact(self, filename: str) -> dict[str, list[str]]:
        """Match filename keywords to framework control tags."""
        tags: dict[str, list[str]] = {}
        fname_lower = filename.lower()
        for keyword, framework_map in EVIDENCE_TAG_MAP.items():
            if keyword in fname_lower:
                for fw, controls in framework_map.items():
                    tags.setdefault(fw, []).extend(controls)
        return tags or {"untagged": []}

    # ── Data Loaders (simulated) ──────────────────────────────────────────────

    def _load_users(self) -> list[dict]:
        user_file = self.data_dir / "users" / "users.json"
        if user_file.exists():
            return json.loads(user_file.read_text())
        return SIMULATED_USERS   # fallback to built-in simulation

    def _load_evidence_manifest(self) -> list[dict]:
        manifest = self.data_dir / "evidence" / "manifest.json"
        if manifest.exists():
            return json.loads(manifest.read_text())
        return SIMULATED_EVIDENCE


# ── Simulated Data ────────────────────────────────────────────────────────────

SIMULATED_USERS = [
    {"id": "u001", "name": "Alice Chen", "role": "Engineer", "employment_status": "active",
     "systems": ["AWS", "GitHub", "Jira"], "last_access": "2025-03-01",
     "manager_review": "approved", "manager_review_date": "2025-01-15", "department": "Engineering"},

    {"id": "u002", "name": "Bob Reyes", "role": "Contractor", "employment_status": "contractor",
     "systems": ["AWS", "Prod-DB", "GitHub"], "last_access": "2025-02-10",
     "manager_review": "pending", "department": "Data"},

    {"id": "u003", "name": "Carol Smith", "role": "Analyst", "employment_status": "terminated",
     "systems": ["Okta", "Jira", "Confluence"], "last_access": "2024-11-30",
     "manager_review": None, "department": "GRC"},

    {"id": "u004", "name": "David Park", "role": "Manager", "employment_status": "active",
     "systems": ["AWS", "Slack", "Salesforce"], "last_access": "2024-07-01",
     "manager_review": "approved", "manager_review_date": "2024-06-01", "department": "Sales"},

    {"id": "u005", "name": "Eva Torres", "role": "Engineer", "employment_status": "active",
     "systems": ["GitHub", "Jira"], "last_access": "2025-04-01",
     "manager_review": None, "department": "Engineering"},
]

SIMULATED_EVIDENCE = [
    {"id": "e001", "filename": "acceptable_use_policy_v3.pdf", "type": "policy",
     "last_reviewed": "2024-03-15", "notes": "Annual review due"},
    {"id": "e002", "filename": "incident_response_plan_v2.pdf", "type": "policy",
     "last_reviewed": "2024-09-01"},
    {"id": "e003", "filename": "security_awareness_training_log_2025.csv", "type": "training_record",
     "last_reviewed": "2025-01-10"},
    {"id": "e004", "filename": "vendor_management_policy.pdf", "type": "policy",
     "last_reviewed": "2023-06-01", "notes": "Significantly overdue for review"},
    {"id": "e005", "filename": "ai_governance_framework_v1.pdf", "type": "policy",
     "last_reviewed": "2025-02-20"},
    {"id": "e006", "filename": "model_monitoring_runbook.pdf", "type": "policy",
     "last_reviewed": None, "notes": "Draft — never formally reviewed"},
    {"id": "e007", "filename": "access_control_matrix_q1_2025.xlsx", "type": "assessment",
     "last_reviewed": "2025-01-30"},
    {"id": "e008", "filename": "risk_assessment_2024.pdf", "type": "assessment",
     "last_reviewed": "2024-12-01"},
    {"id": "e009", "filename": "change_management_procedure.pdf", "type": "policy",
     "last_reviewed": "2024-08-15"},
    {"id": "e010", "filename": "encryption_standards_v2.pdf", "type": "policy",
     "last_reviewed": "2025-03-01"},
]
