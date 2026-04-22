"""
test_questionnaire.py — Run this to test the questionnaire responder
Usage: python test_questionnaire.py
"""

import yaml
import json
from pathlib import Path
import anthropic
from agents.evidence_uar_agent import EvidenceUARAgent
from audit_log.logger import AuditLogger

# ── Load config ───────────────────────────────────────────────────────────────
config = yaml.safe_load(open('config/config.yaml'))
logger = AuditLogger(config["output"]["log_dir"])

# ── Test API key first ────────────────────────────────────────────────────────
print("\nTesting Anthropic API connection...")
try:
    client = anthropic.Anthropic(api_key=config["anthropic"]["api_key"])
    test = client.messages.create(
        model=config["anthropic"]["model"],
        max_tokens=20,
        messages=[{"role": "user", "content": "Say OK"}]
    )
    print("✓ API key works!\n")
except Exception as e:
    print(f"✗ API error: {e}")
    print("\nCheck that your API key is correct in config/config.yaml")
    exit()

# ── Get evidence inventory ────────────────────────────────────────────────────
print("Loading evidence inventory...")
_, evidence = EvidenceUARAgent(config, logger).run()
print(f"✓ {len(evidence)} artifacts loaded\n")

# Build evidence context string
evidence_lines = []
for a in evidence:
    tag_str = ", ".join(
        f"{fw}: {', '.join(ctrls)}"
        for fw, ctrls in a.framework_tags.items()
        if fw != "untagged"
    )
    reviewed = a.last_reviewed or "never reviewed"
    overdue = " OVERDUE" if a.review_overdue else ""
    evidence_lines.append(
        f"- {a.filename} [{a.artifact_type}] | {tag_str} | last reviewed: {reviewed}{overdue}"
    )
evidence_context = "\n".join(evidence_lines)

# ── Questions ─────────────────────────────────────────────────────────────────
questions = [
    "Does your organization have a documented incident response plan tested annually?",
    "How do you manage and review third-party vendor security risks?",
    "What controls do you have in place for AI system governance and oversight?",
]

org = config["audit"]["org_name"]

# ── Answer each question ──────────────────────────────────────────────────────
print("=" * 60)
print("   CUSTOMER SECURITY QUESTIONNAIRE RESPONSES")
print("=" * 60)

for i, question in enumerate(questions, 1):
    print(f"\nQ{i}: {question}")
    print("-" * 60)

    prompt = (
        f"You are a GRC analyst for {org} responding to a customer security questionnaire.\n\n"
        f"Available evidence and policies:\n{evidence_context}\n\n"
        f"Question: {question}\n\n"
        f"Respond ONLY with a JSON object (no markdown, no preamble):\n"
        f'{{"answer": "...", "confidence": "high|medium|low", '
        f'"sources": ["filename1", "filename2"], '
        f'"framework_refs": ["NIST 800-53 AC-2", "SOC 2 CC6.1"]}}\n\n'
        f"Rules:\n"
        f'- "high": strong evidence found, specific artifacts cited\n'
        f'- "medium": partial evidence, inferred from policy\n'
        f'- "low": no direct evidence, best-effort answer\n'
        f"- Keep answer professional and concise (2-4 sentences)\n"
        f"- Never claim compliance you cannot evidence"
    )

    try:
        response = client.messages.create(
            model=config["anthropic"]["model"],
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        clean = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)

        confidence = parsed.get("confidence", "low")
        human_review = confidence == "low"
        review_flag = "⚠ HUMAN REVIEW REQUIRED" if human_review else "✓ Ready to send"

        print(f"A: {parsed.get('answer', 'N/A')}")
        print(f"\nConfidence    : {confidence.upper()}")
        print(f"Review status : {review_flag}")
        print(f"Sources       : {', '.join(parsed.get('sources', [])) or 'None cited'}")
        print(f"Framework refs: {', '.join(parsed.get('framework_refs', [])) or 'None'}")

    except json.JSONDecodeError as e:
        print(f"A: {raw}")  # show raw response if JSON parsing fails
        print(f"(Note: response wasn't clean JSON — {e})")
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "=" * 60)
print("Done! Answers above are AI-drafted and require human review")
print("before sending to any customer.")
print("=" * 60 + "\n")
