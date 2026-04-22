# AI Trust & Audit Agent (ATAA)
### AI-Native GRC Platform | NIST AI RMF · ISO 42001 · NIST 800-53 · SOC 2

A multi-agent AI system for automated governance, risk, and compliance (GRC) auditing. Built to demonstrate how AI can accelerate and enhance the full GRC lifecycle — from control testing and user access reviews to gap analysis and report generation.

> Built by Patricia Mae — GRC Analyst | AI Governance | Risk & Compliance

---

## Screenshots

### Full Audit Pipeline
![Pipeline Output](screenshots/01_pipeline_output.png)

### User Access Review Findings
![UAR Findings](screenshots/02a_uar_findings.png)
![UAR Summary](screenshots/02b_uar_summary.png)

### AI-Drafted Customer Security Questionnaire
![Questionnaire](screenshots/03_questionnaire_response.png)

### Live Audit Dashboard
![Dashboard Overview](screenshots/04_dashboard_overview.png)

### Gap Analysis with AI Remediation
![Gaps](screenshots/05_dashboard_gaps.png)

---

## Architecture

```
Orchestrator
├── Control Tester Agent     → NIST 800-53 control validation + risk scoring
├── Evidence & UAR Agent     → Access reviews + evidence tagging across frameworks
├── Gap Analyzer Agent       → Multi-framework gap scoring + AI remediation
└── Report Drafter Agent     → Audit reports + customer questionnaire responses
```

### Why Multi-Agent?
Each agent has a single responsibility — keeping the system modular, testable, and extensible. The Orchestrator validates outputs between agents so errors are caught at handoff, not downstream.

### Hybrid AI Architecture
- **Deterministic scoring** for control assessment (auditable, reproducible)
- **Claude API** for remediation recommendations and questionnaire drafting (efficient, natural language)
- **Human-in-the-loop** review required before any AI-drafted content is sent externally

---

## Frameworks Covered

| Framework | Coverage |
|---|---|
| NIST SP 800-53 Rev 5 | 30 controls across AC, AU, CM, CP, IA, IR, SA, SC, SI families |
| NIST AI Risk Management Framework | GOVERN · MAP · MEASURE · MANAGE functions |
| ISO/IEC 42001:2023 | Annex A controls for AI management systems |
| SOC 2 Type II | Trust Service Criteria CC6, CC7, CC8, CC9 |

---

## Key Features

**Automated User Access Reviews**
Runs 5 deterministic UAR rules — flags terminated users with active access, contractors with production DB access, dormant accounts, and overdue manager reviews. Maps every finding to NIST 800-53 controls.

**Evidence Collection & Tagging**
Automatically tags evidence artifacts across all four frameworks. Flags overdue reviews and missing evidence for each control.

**Multi-Framework Gap Analysis**
Scores every control across NIST 800-53, NIST AI RMF, ISO 42001, and SOC 2 using a deterministic risk engine (Likelihood × Impact × Control Weight). Generates a 0–100 maturity score per framework.

**AI-Generated Remediation**
Calls Claude API to generate specific, actionable remediation guidance for each gap — citing the relevant framework and control. Deterministic scoring ensures reproducibility; AI handles natural language.

**Customer Security Questionnaire Responder**
Drafts professional answers to customer security questionnaires using your evidence library as context. Includes confidence scoring (high/medium/low) and mandatory human review for low-confidence answers.

**Immutable Audit Log**
Every agent action is recorded in a hash-chained append-only log. Any tampering breaks the chain — verifiable with `python main.py --verify-log`.

**Live React Dashboard**
Interactive dashboard with Framework Maturity Radar, Risk Score bar chart, UAR findings table, expandable gap cards with AI remediation, and strategic recommendations.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/PatitaMae/ai-trust-audit-agent.git
cd ai-trust-audit-agent

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Set up config
cp config/config.example.yaml config/config.yaml
# Add your Anthropic API key to config/config.yaml

# 4. Run the full audit pipeline
python main.py

# 5. Run individual agents
python main.py --agent evidence_uar
python main.py --agent gap_analyzer

# 6. Run questionnaire responder
python main.py --questionnaire

# 7. Verify audit log integrity
python main.py --verify-log

# 8. Launch dashboard
cd ui && npm install && npm run dev
# Open http://localhost:5173
```

---

## Project Structure

```
ai-trust-audit-agent/
├── agents/
│   ├── orchestrator.py          # Workflow router + schema validation
│   ├── control_tester.py        # NIST 800-53 control scoring
│   ├── evidence_uar_agent.py    # UAR rules + evidence tagging
│   ├── gap_analyzer.py          # Multi-framework gap scoring + Claude API
│   └── report_drafter.py        # Report generation + questionnaire drafting
├── scoring/
│   ├── risk_engine.py           # Deterministic risk scoring engine
│   ├── recommendations.json     # Pre-mapped remediation guidance
│   └── cg_score_mapping.json    # Coverage gap scoring rubric
├── frameworks/
│   └── nist_800_53.json         # Control catalog with assessment scores
├── data/
│   ├── asset_inventory.json     # Asset CIA scores and criticality
│   ├── risk_register.json       # Risk register with threat mappings
│   ├── kri_catalog.json         # Key Risk Indicators
│   └── evidence/
│       └── threat_control_map.json  # Threat → control mappings
├── audit_log/
│   └── logger.py                # Hash-chained immutable audit trail
├── ui/
│   └── AuditDashboard.jsx       # React dashboard
├── models.py                    # Shared Pydantic data models
├── main.py                      # CLI entry point
└── requirements.txt
```

---

## Scoring Methodology

Controls are scored across three dimensions:

| Dimension | Question |
|---|---|
| Design Effectiveness | Is the control well-designed on paper? |
| Operating Effectiveness | Is it actually being followed? |
| Evidence Quality | Can you prove it with artifacts? |

```
Risk Score = Likelihood × Impact × Control Weight (0–10)
Maturity   = f(Design, Operating, Evidence)        (0–4 → CMMI scale)
```

This mirrors how Big 4 auditors (Deloitte, PwC, KPMG) assess controls and aligns with GRC platforms like Vanta, AuditBoard, and Drata.

---

## Tech Stack

- **Python 3.10+** — agents, scoring engine, CLI
- **Anthropic Claude API** — remediation generation, questionnaire drafting
- **Pydantic** — data validation between agents
- **React + Vite** — dashboard frontend
- **Recharts** — data visualizations
- **Rich** — terminal output formatting

---

## Roadmap

- [ ] Question Extractor agent — parse questionnaires from PDF/Excel/email automatically
- [ ] Real GRC platform integration (Vanta, Drata API)
- [ ] Scheduled audit runs with trend tracking
- [ ] Export audit reports to PDF
- [ ] SOC 2 evidence package generator

---

## About

Built as a portfolio project to demonstrate AI-native GRC capabilities combining:
- Deep GRC domain knowledge (NIST 800-53, AI RMF, ISO 42001, SOC 2)
- Multi-agent AI system design
- Deterministic risk scoring with LLM augmentation
- Production-grade software patterns (schema validation, immutable audit logs, human-in-the-loop)

**Connect:** [LinkedIn](https://linkedin.com/in/patriciamaesantos  ) | [GitHub](https://github.com/PatitaMae)
