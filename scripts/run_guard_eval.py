#!/usr/bin/env python3
"""Self-test the deterministic contract hash/baseline/write-set guard."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "contract_guard.py"
sys.path.insert(0, str(SCRIPT_DIR))

import contract_guard as cg  # noqa: E402


def run(*args: str, cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(GUARD), *args], cwd=cwd, text=True, capture_output=True)
    if proc.returncode != expect:
        raise RuntimeError(
            f"command failed: {' '.join(args)} expected={expect} actual={proc.returncode}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="slt-guard-eval-") as td:
        root = Path(td)
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "slt@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "SLT Eval"], cwd=root, check=True)

        (root / "allowed.txt").write_text("base\n", encoding="utf-8")
        (root / "forbidden.txt").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

        state = root / ".codex" / "slt-state"
        state.mkdir(parents=True)
        contract_path = state / "EVAL-001.contract.json"
        contract = {
            "id": "EVAL-001",
            "policy_version": cg.POLICY_VERSION,
            "agent_bundle_version": cg.AGENT_BUNDLE_VERSION,
            "base_revision": head,
            "contract_hash": "",
            "goal": "Change only allowed.txt",
            "context": [],
            "read_scope": ["allowed.txt"],
            "allowed_files": ["allowed.txt"],
            "forbidden_files": ["forbidden.txt"],
            "shared_or_generated_files": [],
            "acceptance_criteria": ["allowed.txt changes"],
            "verification": [],
            "integration_verification": [],
            "dependencies": [],
            "execution": {"task_class": "bounded", "bounded_reasoning": "mechanical"},
            "decision_gate": {key: False for key in cg.DECISION_FLAGS},
            "review_risk": {key: False for key in cg.REVIEW_FLAGS},
            "escalation_conditions": [],
        }
        contract["contract_hash"] = cg.compute_contract_hash(contract)
        contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        run("validate-task-contract", "--contract", str(contract_path), cwd=root)
        run("create-task-baseline", "--contract", str(contract_path), cwd=root)

        (root / "allowed.txt").write_text("changed\n", encoding="utf-8")
        run("verify-write-set", "--contract", str(contract_path), cwd=root)

        (root / "unexpected.txt").write_text("oops\n", encoding="utf-8")
        violation = run("verify-write-set", "--contract", str(contract_path), cwd=root, expect=3)
        if "UNDECLARED" not in violation.stdout:
            raise RuntimeError("unexpected file was not classified as UNDECLARED")

        (root / "forbidden.txt").write_text("oops\n", encoding="utf-8")
        violation = run("verify-write-set", "--contract", str(contract_path), cwd=root, expect=3)
        if "FORBIDDEN" not in violation.stdout:
            raise RuntimeError("forbidden file was not classified as FORBIDDEN")

    print("PASS contract guard eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
