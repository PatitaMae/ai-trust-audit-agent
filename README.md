# AI Trust & Audit Agent (ATAA)
### AI-Native GRC Platform | NIST AI RMF · ISO 42001 · NIST 800-53

A multi-agent system for AI governance, risk, and compliance — combining deterministic risk scoring with LLM-powered analysis and report generation.

---

## Architecture

```
Orchestrator
├── Control Tester Agent     → NIST 800-53 control validation
├── Evidence & UAR Agent     → Access reviews + evidence tagging
├── Gap Analyzer Agent       → NIST AI RMF / ISO 42001 / SOC 2 gap scoring
└── Report Drafter Agent     → Audit reports + questionnaire responses
```

## Frameworks Covered
- NIST SP 800-53 Rev 5
- NIST AI Risk Management Framework (GOVERN · MAP · MEASURE · MANAGE)
- ISO/IEC 42001:2023 (Annex A controls)
- SOC 2 Type II (Trust Service Criteria)

## Quick Start

```bash
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
# Add your Anthropic API key to config.yaml

# Run full audit pipeline
python main.py --mode full

# Run individual agent
python main.py --agent gap_analyzer

# Launch web dashboard
cd ui && npm install && npm run dev
```

## Project Structure

```
ai-trust-audit-agent/
├── agents/
│   ├── orchestrator.py          # Workflow router + audit log
│   ├── control_tester.py        # NIST 800-53 control testing
│   ├── evidence_uar_agent.py    # UAR + evidence collection
│   ├── gap_analyzer.py          # Multi-framework gap scoring
│   └── report_drafter.py        # Report + questionnaire drafting
├── scoring/
│   └── risk_engine.py           # Deterministic risk scoring (plug in yours)
├── frameworks/
│   ├── nist_800_53.json         # Control catalog
│   ├── nist_ai_rmf.json         # AI RMF functions + subcategories
│   └── iso_42001.json           # Annex A controls
├── data/
│   ├── users/                   # Simulated UAR data
│   ├── evidence/                # Simulated evidence artifacts
│   └── vendors/                 # Vendor risk data
├── audit_log/
│   └── logger.py                # Immutable audit trail
├── ui/                          # React dashboard
└── reports/                     # Generated audit outputs
```
