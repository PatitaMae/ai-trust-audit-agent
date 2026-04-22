"""
audit_log/logger.py — Immutable append-only audit trail
Every agent action is recorded with timestamp, agent name, and payload.
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path


class AuditLogger:
    """
    Append-only audit log. Each entry includes a hash of the previous
    entry, forming a chain — any tampering breaks the chain integrity.
    """

    def __init__(self, log_dir: str = "./audit_log/logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"audit_{datetime.utcnow().strftime('%Y%m%d')}.jsonl"
        self._last_hash = self._get_last_hash()

    def _get_last_hash(self) -> str:
        """Read the hash of the last entry to chain the log."""
        if not self.log_file.exists():
            return "GENESIS"
        lines = self.log_file.read_text().strip().splitlines()
        if not lines:
            return "GENESIS"
        return json.loads(lines[-1]).get("entry_hash", "GENESIS")

    def log(self, agent: str, action: str, payload: dict, severity: str = "info") -> dict:
        """Append a new entry to the audit log."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
            "severity": severity,
            "payload": payload,
            "prev_hash": self._last_hash,
        }
        entry_str = json.dumps(entry, sort_keys=True)
        entry["entry_hash"] = hashlib.sha256(entry_str.encode()).hexdigest()

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        self._last_hash = entry["entry_hash"]
        return entry

    def verify_chain(self) -> bool:
        """Verify log integrity — returns False if any entry was tampered with."""
        if not self.log_file.exists():
            return True
        lines = self.log_file.read_text().strip().splitlines()
        prev_hash = "GENESIS"
        for line in lines:
            entry = json.loads(line)
            if entry.get("prev_hash") != prev_hash:
                return False
            # Recompute hash without the entry_hash field
            check = {k: v for k, v in entry.items() if k != "entry_hash"}
            computed = hashlib.sha256(
                json.dumps(check, sort_keys=True).encode()
            ).hexdigest()
            if computed != entry.get("entry_hash"):
                return False
            prev_hash = entry["entry_hash"]
        return True

    def tail(self, n: int = 20) -> list[dict]:
        """Return the last n log entries."""
        if not self.log_file.exists():
            return []
        lines = self.log_file.read_text().strip().splitlines()
        return [json.loads(l) for l in lines[-n:]]
