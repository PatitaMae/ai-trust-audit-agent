"""
test_uar.py — Run this to see your Evidence & UAR agent output
Usage: python test_uar.py
"""

import yaml
from agents.evidence_uar_agent import EvidenceUARAgent
from audit_log.logger import AuditLogger

config = yaml.safe_load(open('config/config.yaml'))
logger = AuditLogger(config['output']['log_dir'])
agent = EvidenceUARAgent(config, logger)
findings, evidence = agent.run()

print('\n' + '='*50)
print('       UAR FINDINGS')
print('='*50)
for f in findings:
    print(f'\n[{f.severity.upper()}] {f.user_name}')
    print(f'  Finding : {f.description}')
    print(f'  Systems : {", ".join(f.systems_affected)}')
    print(f'  Action  : {f.recommended_action}')
    print(f'  Control : {f.control_ref}')

print('\n' + '='*50)
print(f'  EVIDENCE INVENTORY ({len(evidence)} artifacts)')
print('='*50)
for e in evidence:
    overdue = ' ⚠ OVERDUE' if e.review_overdue else ' ✓'
    print(f'\n  {e.filename}{overdue}')
    for fw, controls in e.framework_tags.items():
        if fw != 'untagged':
            print(f'    {fw}: {", ".join(controls)}')

print('\n' + '='*50)
print(f'  SUMMARY')
print('='*50)
critical = sum(1 for f in findings if f.severity == 'critical')
high     = sum(1 for f in findings if f.severity == 'high')
medium   = sum(1 for f in findings if f.severity == 'medium')
low      = sum(1 for f in findings if f.severity == 'low')
overdue  = sum(1 for e in evidence if e.review_overdue)
print(f'  UAR Findings  : {len(findings)} total')
print(f'    Critical    : {critical}')
print(f'    High        : {high}')
print(f'    Medium      : {medium}')
print(f'    Low         : {low}')
print(f'  Evidence      : {len(evidence)} artifacts')
print(f'  Overdue Review: {overdue}')
print()
