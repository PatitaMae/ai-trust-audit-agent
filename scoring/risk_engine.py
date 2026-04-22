"""
scoring/risk_engine.py — Deterministic risk scoring engine
─────────────────────────────────────────────────────────
Patricia: This is the plug-in point for your existing scoring logic.
Replace or extend the calculate() method with your own algorithm.
The interface (inputs/outputs) should stay consistent so the
Gap Analyzer and Control Tester can consume scores reliably.
"""

from models import MaturityScore


# Control criticality weights — higher = more impactful to overall risk posture
# Extend this with your own weights or load from a JSON config
CONTROL_WEIGHTS: dict[str, float] = {
    # Access Control
    "AC-2":  0.90,  "AC-3":  0.85,  "AC-6":  0.88,
    # Audit & Accountability
    "AU-2":  0.80,  "AU-9":  0.85,
    # Configuration Management
    "CM-6":  0.75,  "CM-7":  0.80,
    # Incident Response
    "IR-4":  0.88,  "IR-6":  0.82,
    # Risk Assessment
    "RA-3":  0.85,  "RA-5":  0.90,
    # System & Comms Protection
    "SC-8":  0.80,  "SC-28": 0.85,
    # AI RMF functions (weighted by governance criticality)
    "GOVERN-1.1": 0.90, "GOVERN-1.2": 0.85,
    "MAP-1.1":    0.80, "MAP-2.2":    0.82,
    "MEASURE-2.5": 0.88, "MEASURE-2.6": 0.85,
    "MANAGE-1.3": 0.87, "MANAGE-2.2": 0.83,
    # ISO 42001
    "A.6.1": 0.88, "A.6.2": 0.85,
    "A.9.1": 0.90, "A.9.2": 0.87,
}

DEFAULT_WEIGHT = 0.75


class RiskEngine:
    """
    Deterministic risk scorer.

    Risk Score = Likelihood × Impact × Control Weight
    Scale: 0.0 – 10.0

    Design, Operating, and Evidence sub-scores feed into
    Likelihood and Impact calculations respectively.
    """

    def __init__(self, likelihood_weight: float = 0.4, impact_weight: float = 0.6):
        self.likelihood_weight = likelihood_weight
        self.impact_weight = impact_weight

    def calculate(
        self,
        control_id: str,
        design_score: int,      # 0-4: how well-designed is the control?
        operating_score: int,   # 0-4: is it actually being followed?
        evidence_score: int,    # 0-4: can you prove it with artifacts?
    ) -> dict:
        """
        Returns a full risk assessment dict for a single control.

        ── REPLACE THIS METHOD with your existing scoring logic ──
        Keep the return shape consistent so downstream agents work.
        """
        if not all(0 <= s <= 4 for s in [design_score, operating_score, evidence_score]):
            raise ValueError("All sub-scores must be between 0 and 4")

        weight = CONTROL_WEIGHTS.get(control_id, DEFAULT_WEIGHT)

        # Gaps from perfect score (4)
        design_gap    = (4 - design_score)    / 4
        operating_gap = (4 - operating_score) / 4
        evidence_gap  = (4 - evidence_score)  / 4

        # Likelihood: how likely is a control failure?
        # Poor operating effectiveness + poor evidence = high likelihood
        likelihood = (
            (operating_gap * 0.6) +
            (evidence_gap  * 0.4)
        )

        # Impact: how bad is the gap?
        # Poor design = fundamental weakness, higher impact
        impact = (
            (design_gap    * 0.5) +
            (operating_gap * 0.3) +
            (evidence_gap  * 0.2)
        )

        raw_score = (
            (likelihood * self.likelihood_weight) +
            (impact     * self.impact_weight)
        ) * weight * 10

        risk_score = round(min(raw_score, 10.0), 2)
        maturity = self._to_maturity(design_score, operating_score, evidence_score)

        return {
            "control_id":            control_id,
            "risk_score":            risk_score,
            "risk_level":            self._risk_level(risk_score),
            "maturity":              maturity,
            "likelihood":            round(likelihood, 3),
            "impact":                round(impact, 3),
            "control_weight":        weight,
            "design_score":          design_score,
            "operating_score":       operating_score,
            "evidence_score":        evidence_score,
        }

    def _to_maturity(self, d: int, o: int, e: int) -> MaturityScore:
        """Derive overall maturity from the three sub-scores."""
        avg = (d + o + e) / 3
        if avg >= 3.5: return MaturityScore.OPTIMIZED
        if avg >= 2.5: return MaturityScore.MANAGED
        if avg >= 1.5: return MaturityScore.IN_DEVELOPMENT
        if avg >= 0.5: return MaturityScore.INITIAL
        return MaturityScore.INCOMPLETE

    def _risk_level(self, score: float) -> str:
        if score >= 8.0: return "critical"
        if score >= 6.0: return "high"
        if score >= 4.0: return "medium"
        if score >= 2.0: return "low"
        return "info"

    def batch_calculate(self, controls: list[dict]) -> list[dict]:
        """Score a list of controls. Each dict needs control_id + 3 sub-scores."""
        return [
            self.calculate(
                c["control_id"],
                c.get("design_score", 2),
                c.get("operating_score", 2),
                c.get("evidence_score", 1),
            )
            for c in controls
        ]
