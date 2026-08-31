#!/usr/bin/env python3
"""Self-test SLT contract hashing, sealed baselines, ignored files, casing, and locks."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
GUARD = SCRIPT_DIR / "contract_guard.py"
LOCK = SCRIPT_DIR / "writer_lock.py"
sys.path.insert(0, str(SCRIPT_DIR))

import contract_guard as cg  # noqa: E402
import writer_lock as wl  # noqa: E402


def run_tool(tool: Path, *args: str, cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(tool), *args], cwd=cwd, text=True, capture_output=True)
    if proc.returncode != expect:
        raise RuntimeError(
            f"command failed: {tool.name} {' '.join(args)} expected={expect} actual={proc.returncode}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc


def write_contract(path: Path, head: str, *, task_id: str = "EVAL-001") -> dict:
    contract = {
        "id": task_id,
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
        "snapshot_exclude": [],
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
    path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return contract


def baseline_info(contract_path: Path, root: Path) -> tuple[Path, str]:
    out = run_tool(GUARD, "create-task-baseline", "--contract", str(contract_path), "--json", cwd=root)
    data = json.loads(out.stdout)
    return Path(data["baseline"]).resolve(), data["baseline_sha256"]


def verify(contract_path: Path, seal: str, root: Path, *, expect: int = 0) -> subprocess.CompletedProcess[str]:
    return run_tool(
        GUARD,
        "verify-write-set",
        "--contract", str(contract_path),
        "--baseline-sha", seal,
        cwd=root,
        expect=expect,
    )


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="slt-guard-eval-") as td:
        root = Path(td).resolve()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "slt@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "SLT Eval"], cwd=root, check=True)
        (root / ".gitignore").write_text("*.secret\n", encoding="utf-8")
        (root / "allowed.txt").write_text("base\n", encoding="utf-8")
        (root / "forbidden.txt").write_text("base\n", encoding="utf-8")
        (root / "binary.bin").write_bytes(b"\x00\x01base")
        (root / "hidden.secret").write_text("ignored-base\n", encoding="utf-8")
        subprocess.run(["git", "add", ".gitignore", "allowed.txt", "forbidden.txt", "binary.bin"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=root, check=True)
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

        state = root / ".codex" / "slt-state"
        state.mkdir(parents=True)
        contract_path = state / "EVAL-001.contract.json"
        original = write_contract(contract_path, head)

        run_tool(LOCK, "acquire", "--task-id", "EVAL-001", cwd=root)
        lock_path = wl.lock_path(root)
        if root != lock_path and root not in lock_path.parents:
            raise RuntimeError("default writer lock must be workspace-local")
        run_tool(LOCK, "acquire", "--task-id", "OTHER", cwd=root, expect=3)

        run_tool(GUARD, "validate-task-contract", "--contract", str(contract_path), cwd=root)
        baseline_path, seal = baseline_info(contract_path, root)
        if root != baseline_path and root not in baseline_path.parents:
            raise RuntimeError("default baseline must be workspace-local")
        if not baseline_path.is_file() or seal != cg.sha256_file(baseline_path):
            raise RuntimeError("baseline/seal creation failed")

        (root / "allowed.txt").write_text("changed\n", encoding="utf-8")
        verify(contract_path, seal, root)
        (root / "allowed.txt").write_text("base\n", encoding="utf-8")

        (root / "hidden.secret").write_text("mutated\n", encoding="utf-8")
        out = verify(contract_path, seal, root, expect=3)
        if "UNDECLARED" not in out.stdout or "hidden.secret" not in out.stdout:
            raise RuntimeError("ignored file mutation was not detected")
        (root / "hidden.secret").write_text("ignored-base\n", encoding="utf-8")

        (root / "new.secret").write_text("new\n", encoding="utf-8")
        if "new.secret" not in verify(contract_path, seal, root, expect=3).stdout:
            raise RuntimeError("new ignored file was not detected")
        (root / "new.secret").unlink()

        (root / "unexpected.txt").write_text("oops\n", encoding="utf-8")
        if "UNDECLARED" not in verify(contract_path, seal, root, expect=3).stdout:
            raise RuntimeError("unexpected file was not UNDECLARED")
        (root / "unexpected.txt").unlink()

        (root / "forbidden.txt").write_text("oops\n", encoding="utf-8")
        if "FORBIDDEN" not in verify(contract_path, seal, root, expect=3).stdout:
            raise RuntimeError("forbidden file was not FORBIDDEN")
        (root / "forbidden.txt").write_text("base\n", encoding="utf-8")

        (root / "binary.bin").write_bytes(b"\x00\x02changed")
        if "binary.bin" not in verify(contract_path, seal, root, expect=3).stdout:
            raise RuntimeError("binary mutation was not detected")
        (root / "binary.bin").write_bytes(b"\x00\x01base")

        (root / "allowed.txt").unlink()
        verify(contract_path, seal, root)
        (root / "allowed.txt").write_text("base\n", encoding="utf-8")

        os.rename(root / "allowed.txt", root / "renamed.txt")
        if "renamed.txt" not in verify(contract_path, seal, root, expect=3).stdout:
            raise RuntimeError("rename target was not detected")
        os.rename(root / "renamed.txt", root / "allowed.txt")

        pivot = root / "__slt_case_pivot__.tmp"
        os.rename(root / "allowed.txt", pivot)
        os.rename(pivot, root / "ALLOWED.txt")
        out = verify(contract_path, seal, root, expect=3)
        if "ALLOWED.txt" not in out.stdout:
            raise RuntimeError("case-only rename target was not detected")
        os.rename(root / "ALLOWED.txt", pivot)
        os.rename(pivot, root / "allowed.txt")

        if hasattr(os, "symlink"):
            try:
                os.symlink("allowed.txt", root / "link.txt")
            except (OSError, NotImplementedError) as exc:
                print(f"SKIP symlink eval: {exc}")
            else:
                if "link.txt" not in verify(contract_path, seal, root, expect=3).stdout:
                    raise RuntimeError("symlink creation was not detected")
                (root / "link.txt").unlink()
        else:
            print("SKIP symlink eval: os.symlink unavailable")

        baseline_bytes = baseline_path.read_bytes()
        tampered_baseline = json.loads(baseline_bytes)
        tampered_baseline["tampered"] = True
        baseline_path.write_text(json.dumps(tampered_baseline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out = verify(contract_path, seal, root, expect=2)
        if "baseline SHA mismatch" not in out.stderr:
            raise RuntimeError("baseline tampering was not rejected")
        baseline_path.write_bytes(baseline_bytes)

        tampered = dict(original)
        tampered["goal"] = "tampered"
        tampered["contract_hash"] = cg.compute_contract_hash(tampered)
        contract_path.write_text(json.dumps(tampered, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        out = verify(contract_path, seal, root, expect=2)
        if "baseline contract_hash" not in out.stderr:
            raise RuntimeError("contract tampering was not rejected")
        contract_path.write_text(json.dumps(original, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        run_tool(LOCK, "release", "--task-id", "EVAL-001", cwd=root)

        stale_path = state / "STALE.contract.json"
        write_contract(stale_path, "0" * 40, task_id="STALE")
        run_tool(LOCK, "acquire", "--task-id", "STALE", cwd=root)
        out = run_tool(GUARD, "create-task-baseline", "--contract", str(stale_path), "--json", cwd=root, expect=2)
        if "does not match HEAD" not in out.stderr:
            raise RuntimeError("stale base_revision was not rejected")
        run_tool(LOCK, "release", "--task-id", "STALE", cwd=root)

    print("PASS contract guard eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
