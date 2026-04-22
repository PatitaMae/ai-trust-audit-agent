"""
models.py — Shared Pydantic data models for ATAA
All agents consume and produce these validated structures.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from enum import IntEnum


# ─────────────────────────────────────────────
# SCORING
# ─────────────────────────────────────────────

class MaturityScore(IntEnum):
    INCOMPLETE    = 0   # Not addressed
    INITIAL       = 1   # Planned, not started
    IN_DEVELOPMENT = 2  # In progress, no evidence
    MANAGED       = 3   # Implemented, evidence incomplete
    OPTIMIZED     = 4   # Fully implemented + evidence exists


class RiskLevel(str):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    INFO     = "info"


class ControlScore(BaseModel):
    control_id: str
    framework: str
    score: MaturityScore
    design_effectiveness: int = Field(ge=0, le=4)
    operating_effectiveness: int = Field(ge=0, le=4)
    evidence_quality: int = Field(ge=0, le=4)
    risk_score: float = Field(ge=0.0, le=10.0)
    notes: Optional[str] = None
    evidence_refs: list[str] = []
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# UAR
# ─────────────────────────────────────────────

class UserRecord(BaseModel):
    id: str
    name: str
    role: str
    employment_status: Literal["active", "terminated", "on_leave", "contractor"]
    systems: list[str]
    last_access: Optional[str] = None       # ISO date string
    manager_review: Optional[str] = None   # "approved" | "pending" | None
    manager_review_date: Optional[str] = None
    department: Optional[str] = None


class UARFinding(BaseModel):
    user_id: str
    user_name: str
    severity: str   # critical | high | medium | low
    rule_triggered: str
    description: str
    systems_affected: list[str]
    recommended_action: str
    control_ref: str  # e.g. "AC-2"


# ─────────────────────────────────────────────
# EVIDENCE
# ─────────────────────────────────────────────

class EvidenceArtifact(BaseModel):
    id: str
    filename: str
    artifact_type: Literal["policy", "log", "training_record", "assessment", "attestation"]
    framework_tags: dict[str, list[str]]  # {"soc2": ["CC9.9"], "nist_800_53": ["AC-1"]}
    last_reviewed: Optional[str] = None
    review_overdue: bool = False
    notes: Optional[str] = None


# ─────────────────────────────────────────────
# GAP ANALYSIS
# ─────────────────────────────────────────────

class GapFinding(BaseModel):
    control_id: str
    framework: str
    description: str
    current_score: MaturityScore
    risk_score: float
    risk_level: str
    remediation: str        # LLM-generated
    effort: Literal["Low", "Medium", "High"]
    priority: int
    evidence_missing: list[str]


class FrameworkGapReport(BaseModel):
    framework: str
    total_controls: int
    compliant: int      # score 4
    partial: int        # score 3
    in_development: int # score 2
    gaps: int           # score 0-1
    critical_gaps: list[GapFinding]
    maturity_score: float   # 0-100 composite
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


# ─────────────────────────────────────────────
# REPORT DRAFTER
# ─────────────────────────────────────────────

class QuestionnaireResponse(BaseModel):
    question: str
    answer: str             # LLM-drafted
    confidence: Literal["high", "medium", "low"]
    sources: list[str]      # evidence artifact IDs
    human_review_required: bool
    framework_refs: list[str]


class AuditReport(BaseModel):
    org_name: str
    report_type: Literal["executive", "technical", "gap", "questionnaire"]
    frameworks_assessed: list[str]
    overall_maturity_score: float
    critical_finding_count: int
    high_finding_count: int
    gap_reports: list[FrameworkGapReport]
    uar_findings: list[UARFinding]
    recommendations: list[str]
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    human_reviewed: bool = False
