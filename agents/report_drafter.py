"""
agents/report_drafter.py — Audit Report + Questionnaire Drafting Agent
────────────────────────────────────────────────────────────────────────
Uses Claude API to:
  1. Draft executive + technical audit reports from gap analysis output
  2. Answer customer security questionnaires using evidence library context

Human review is always required before questionnaire answers are sent.
Confidence scoring determines when human escalation is mandatory.
"""

import json
from datetime import datetime
from pathlib import Path

import anthropic

from audit_log.logger import AuditLogger
from models import (
    AuditReport, FrameworkGapReport, UARFinding,
    EvidenceArtifact, QuestionnaireResponse
)


HUMAN_REVIEW_THRESHOLD = 0.70  # confidence below this = mandatory human review


class ReportDrafterAgent:
    def __init__(self, config: dict, logger: AuditLogger):
        self.config = config
        self.logger = logger
        self.client = anthropic.Anthropic(api_key=config["anthropic"]["api_key"])
        self.model = config["anthropic"]["model"]
        self.org = config["audit"]["org_name"]

    # ────────────────────────────────────────────────────────────────────────
    # MAIN: Full Audit Report
    # ────────────────────────────────────────────────────────────────────────

    def run(
        self,
        gap_reports: list[FrameworkGapReport],
        uar_findings: list[UARFinding],
        evidence_inventory: list[EvidenceArtifact],
    ) -> AuditReport:
        """Generate a complete AuditReport from pipeline outputs."""
        self.logger.log("report_drafter", "run_start", {})

        critical_count = sum(len(r.critical_gaps) for r in gap_reports
                             if r.critical_gaps)
        high_count = sum(
            1 for r in gap_reports
            for g in (r.critical_gaps or [])
            if g.risk_level == "high"
        )

        # Overall maturity = average across frameworks
        overall_maturity = round(
            sum(r.maturity_score for r in gap_reports) / len(gap_reports), 1
        ) if gap_reports else 0.0

        recommendations = self._generate_recommendations(gap_reports, uar_findings)

        report = AuditReport(
            org_name=self.org,
            report_type="technical",
            frameworks_assessed=[r.framework for r in gap_reports],
            overall_maturity_score=overall_maturity,
            critical_finding_count=critical_count,
            high_finding_count=high_count,
            gap_reports=gap_reports,
            uar_findings=uar_findings,
            recommendations=recommendations,
        )

        # Persist report to disk
        self._save_report(report)

        self.logger.log("report_drafter", "run_complete", {
            "overall_maturity": overall_maturity,
            "critical_findings": critical_count,
        })

        return report

    def _generate_recommendations(
        self,
        gap_reports: list[FrameworkGapReport],
        uar_findings: list[UARFinding],
    ) -> list[str]:
        """Use Claude to generate top strategic recommendations."""
        # Build a structured context summary for the LLM
        gap_summary = "\n".join([
            f"- {r.framework.upper()}: {r.gaps} gaps, maturity {r.maturity_score}/100, "
            f"{len(r.critical_gaps)} critical"
            for r in gap_reports
        ])
        uar_summary = (
            f"{sum(1 for f in uar_findings if f.severity == 'critical')} critical UAR findings, "
            f"{sum(1 for f in uar_findings if f.severity == 'high')} high"
        )

        prompt = (
            f"You are a senior GRC analyst at {self.org} preparing an executive summary.\n\n"
            f"Framework gap analysis:\n{gap_summary}\n\n"
            f"User Access Review: {uar_summary}\n\n"
            f"Write exactly 5 strategic recommendations for leadership. "
            f"Each recommendation should be one clear, actionable sentence. "
            f"Return as a JSON array of strings only, no preamble."
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            clean = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(clean)
        except Exception as e:
            self.logger.log("report_drafter", "llm_error", {"error": str(e)}, severity="error")
            return [
                "Remediate all critical UAR findings within 72 hours.",
                "Establish AI governance policy aligned to NIST AI RMF GOVERN function.",
                "Implement post-deployment model monitoring per MEASURE-2.5.",
                "Conduct vendor risk assessments for all Tier 1 suppliers.",
                "Resolve evidence gaps for controls with scores below 2.",
            ]

    # ────────────────────────────────────────────────────────────────────────
    # QUESTIONNAIRE RESPONDER
    # ────────────────────────────────────────────────────────────────────────

    def answer_questionnaire(
        self,
        questions: list[str],
        evidence_inventory: list[EvidenceArtifact],
    ) -> list[QuestionnaireResponse]:
        """
        Draft answers to customer security questionnaire questions.
        Always routes low-confidence answers to human review queue.
        """
        self.logger.log("report_drafter", "questionnaire_start", {
            "question_count": len(questions)
        })

        evidence_context = self._build_evidence_context(evidence_inventory)
        responses = []

        for question in questions:
            response = self._draft_answer(question, evidence_context)
            responses.append(response)

            self.logger.log("report_drafter", "questionnaire_answer_drafted", {
                "confidence": response.confidence,
                "human_review_required": response.human_review_required,
                "sources_found": len(response.sources),
            })

        return responses

    def _draft_answer(
        self,
        question: str,
        evidence_context: str,
    ) -> QuestionnaireResponse:
        """Draft a single questionnaire answer with confidence scoring."""
        prompt = (
            f"You are a GRC analyst for {self.org} responding to a customer security questionnaire.\n\n"
            f"Available evidence and policies:\n{evidence_context}\n\n"
            f"Question: {question}\n\n"
            f"Respond ONLY with a JSON object (no markdown, no preamble):\n"
            f'{{"answer": "...", "confidence": "high|medium|low", '
            f'"sources": ["filename1", "filename2"], '
            f'"framework_refs": ["NIST 800-53 AC-2", "SOC 2 CC6.1"]}}\n\n'
            f'Rules:\n'
            f'- "high" confidence: strong evidence found, specific artifacts cited\n'
            f'- "medium" confidence: partial evidence, inferred from policy\n'  
            f'- "low" confidence: no direct evidence, answer is best-effort\n'
            f'- Keep answer professional, concise (2-4 sentences)\n'
            f'- Never claim compliance you cannot evidence'
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()
            clean = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean)

            confidence = parsed.get("confidence", "low")
            confidence_score = {"high": 0.9, "medium": 0.65, "low": 0.3}.get(confidence, 0.3)

            return QuestionnaireResponse(
                question=question,
                answer=parsed.get("answer", "Unable to generate answer."),
                confidence=confidence,
                sources=parsed.get("sources", []),
                human_review_required=confidence_score < HUMAN_REVIEW_THRESHOLD,
                framework_refs=parsed.get("framework_refs", []),
            )

        except Exception as e:
            self.logger.log("report_drafter", "questionnaire_llm_error",
                            {"error": str(e)}, severity="error")
            return QuestionnaireResponse(
                question=question,
                answer="Unable to draft answer — manual response required.",
                confidence="low",
                sources=[],
                human_review_required=True,
                framework_refs=[],
            )

    def _build_evidence_context(self, evidence: list[EvidenceArtifact]) -> str:
        """Summarize evidence inventory for LLM context."""
        lines = []
        for a in evidence:
            tag_str = ", ".join(
                f"{fw}: {', '.join(ctrls)}"
                for fw, ctrls in a.framework_tags.items()
                if fw != "untagged"
            )
            reviewed = a.last_reviewed or "never reviewed"
            overdue_flag = " ⚠️ OVERDUE" if a.review_overdue else ""
            lines.append(
                f"- {a.filename} [{a.artifact_type}] | {tag_str} | "
                f"last reviewed: {reviewed}{overdue_flag}"
            )
        return "\n".join(lines)

    def _save_report(self, report: AuditReport) -> None:
        """Save report as JSON to reports directory."""
        reports_dir = Path(self.config["output"]["reports_dir"])
        reports_dir.mkdir(parents=True, exist_ok=True)
        filename = reports_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filename.write_text(report.model_dump_json(indent=2))
        self.logger.log("report_drafter", "report_saved", {"path": str(filename)})
