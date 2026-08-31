#!/usr/bin/env python3
"""Deterministic helpers for SLT task contracts and write-boundary verification.

The semantic classification of a task remains a model/user judgment. Once a contract exists,
this tool deterministically validates its shape/version/hash, snapshots the current worktree,
and verifies the resulting write set.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

POLICY_VERSION = "0.3.0"
AGENT_BUNDLE_VERSION = "0.3.0"

DECISION_FLAGS = (
    "unresolved_architecture",
    "ambiguous_requirement",
    "competing_root_causes",
    "contract_expansion_required",
    "unresolved_security_policy",
    "external_contract_unknown",
    "migration_strategy_unresolved",
    "concurrency_semantics_unresolved",
    "irreversible_operation_unresolved",
    "repeated_failure",
)

REVIEW_FLAGS = (
    "public_contract_touched",
    "schema_or_migration_touched",
    "auth_or_permission_touched",
    "concurrency_or_transaction_touched",
    "irreversible_operation_touched",
    "new_dependency_or_protocol_touched",
    "weak_test_oracle",
    "generated_or_shared_artifact_touched",
    "repeated_failure_or_flaky",
)

REQUIRED_FIELDS = (
    "id",
    "policy_version",
    "agent_bundle_version",
    "base_revision",
    "goal",
    "context",
    "read_scope",
    "allowed_files",
    "forbidden_files",
    "shared_or_generated_files",
    "acceptance_criteria",
    "verification",
    "integration_verification",
    "dependencies",
    "execution",
    "decision_gate",
    "review_risk",
    "escalation_conditions",
)

LIST_FIELDS = (
    "context",
    "read_scope",
    "allowed_files",
    "forbidden_files",
    "shared_or_generated_files",
    "acceptance_criteria",
    "verification",
    "integration_verification",
    "dependencies",
    "escalation_conditions",
)


class GuardError(Exception):
    pass


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardError(f"expected JSON object in {path}")
    return data


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def canonical_contract(contract: dict[str, Any]) -> bytes:
    material = {k: v for k, v in contract.items() if k != "contract_hash"}
    return json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_contract_hash(contract: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_contract(contract)).hexdigest()


def validate_bool_map(name: str, value: Any, expected_keys: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict):
        return [f"{name} must be an object"]
    expected = set(expected_keys)
    actual = set(value)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing:
        errors.append(f"{name} missing keys: {', '.join(missing)}")
    if extra:
        errors.append(f"{name} has unknown keys: {', '.join(extra)}")
    for key in sorted(expected & actual):
        if not isinstance(value[key], bool):
            errors.append(f"{name}.{key} must be boolean")
    return errors


def validate_contract(contract: dict[str, Any], require_hash: bool = True) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in contract:
            errors.append(f"missing required field: {field}")

    if contract.get("policy_version") != POLICY_VERSION:
        errors.append(f"policy_version must be {POLICY_VERSION}")
    if contract.get("agent_bundle_version") != AGENT_BUNDLE_VERSION:
        errors.append(f"agent_bundle_version must be {AGENT_BUNDLE_VERSION}")

    for field in LIST_FIELDS:
        if field in contract and not isinstance(contract[field], list):
            errors.append(f"{field} must be an array")

    for field in ("allowed_files", "forbidden_files", "shared_or_generated_files", "read_scope"):
        if field in contract and isinstance(contract[field], list):
            for i, item in enumerate(contract[field]):
                if not isinstance(item, str) or not item.strip():
                    errors.append(f"{field}[{i}] must be a non-empty string")

    for field in ("id", "goal", "base_revision"):
        if field in contract and (not isinstance(contract[field], str) or not contract[field].strip()):
            errors.append(f"{field} must be a non-empty string")

    execution = contract.get("execution")
    if not isinstance(execution, dict):
        errors.append("execution must be an object")
    else:
        task_class = execution.get("task_class")
        if task_class not in ("trivial", "bounded", "complex_decided"):
            errors.append("execution.task_class must be trivial|bounded|complex_decided")
        bounded_reasoning = execution.get("bounded_reasoning")
        if task_class == "bounded" and bounded_reasoning not in ("mechanical", "logic"):
            errors.append("bounded execution requires bounded_reasoning=mechanical|logic")
        if task_class != "bounded" and bounded_reasoning not in (None, ""):
            errors.append("bounded_reasoning is only valid for bounded tasks")

    errors.extend(validate_bool_map("decision_gate", contract.get("decision_gate"), DECISION_FLAGS))
    errors.extend(validate_bool_map("review_risk", contract.get("review_risk"), REVIEW_FLAGS))

    allowed = set(contract.get("allowed_files", [])) if isinstance(contract.get("allowed_files"), list) else set()
    forbidden = set(contract.get("forbidden_files", [])) if isinstance(contract.get("forbidden_files"), list) else set()
    overlap = sorted(allowed & forbidden)
    if overlap:
        errors.append("paths cannot be both allowed and forbidden: " + ", ".join(overlap))

    if require_hash:
        actual = contract.get("contract_hash")
        expected = compute_contract_hash(contract)
        if not isinstance(actual, str) or not actual:
            errors.append("missing contract_hash")
        elif actual != expected:
            errors.append(f"contract_hash mismatch: expected {expected}, got {actual}")

    return errors


def git_root(start: Path | None = None) -> Path:
    cwd = str(start or Path.cwd())
    proc = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GuardError("not inside a Git worktree")
    return Path(proc.stdout.strip()).resolve()


def git_head(root: Path) -> str:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else "UNBORN"


def worktree_paths(root: Path) -> list[str]:
    proc = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"], capture_output=True)
    if proc.returncode != 0:
        raise GuardError(proc.stderr.decode("utf-8", errors="replace").strip() or "git ls-files failed")
    paths: list[str] = []
    for item in proc.stdout.split(b"\0"):
        if not item:
            continue
        rel = item.decode("utf-8", errors="surrogateescape").replace(os.sep, "/")
        if rel == ".codex/slt-state" or rel.startswith(".codex/slt-state/"):
            continue
        paths.append(rel)
    return sorted(set(paths))


def hash_path(path: Path) -> str:
    if path.is_symlink():
        payload = ("SYMLINK\0" + os.readlink(path)).encode("utf-8", errors="surrogateescape")
        return hashlib.sha256(payload).hexdigest()
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in worktree_paths(root):
        p = root / rel
        if p.is_file() or p.is_symlink():
            result[rel] = hash_path(p)
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def matches(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def default_baseline_path(root: Path, task_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_." else "_" for c in task_id)
    return root / ".codex" / "slt-state" / f"{safe}.baseline.json"


def cmd_hash(args: argparse.Namespace) -> int:
    path = Path(args.contract)
    contract = load_json(path)
    value = compute_contract_hash(contract)
    if args.write:
        contract["contract_hash"] = value
        save_json(path, contract)
    print(value)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    contract = load_json(Path(args.contract))
    errors = validate_contract(contract, require_hash=not args.allow_missing_hash)
    if errors:
        for error in errors:
            eprint("ERROR:", error)
        return 2
    print(f"VALID {contract['id']} {compute_contract_hash(contract)}")
    return 0


def cmd_baseline(args: argparse.Namespace) -> int:
    root = git_root(Path(args.repo) if args.repo else None)
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = (root / contract_path).resolve()
    contract = load_json(contract_path)
    errors = validate_contract(contract, require_hash=True)
    if errors:
        for error in errors:
            eprint("ERROR:", error)
        return 2
    baseline = {
        "format_version": 1,
        "task_id": contract["id"],
        "contract_hash": contract["contract_hash"],
        "policy_version": POLICY_VERSION,
        "agent_bundle_version": AGENT_BUNDLE_VERSION,
        "git_head": git_head(root),
        "snapshot": snapshot(root),
    }
    out = Path(args.output).resolve() if args.output else default_baseline_path(root, contract["id"])
    save_json(out, baseline)
    print(out)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    root = git_root(Path(args.repo) if args.repo else None)
    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = (root / contract_path).resolve()
    contract = load_json(contract_path)
    errors = validate_contract(contract, require_hash=True)
    if errors:
        for error in errors:
            eprint("ERROR:", error)
        return 2

    baseline_path = Path(args.baseline).resolve() if args.baseline else default_baseline_path(root, contract["id"])
    baseline = load_json(baseline_path)
    if baseline.get("task_id") != contract["id"]:
        raise GuardError("baseline task_id does not match contract")
    if baseline.get("contract_hash") != contract["contract_hash"]:
        raise GuardError("baseline contract_hash does not match current contract")
    if baseline.get("policy_version") != POLICY_VERSION or baseline.get("agent_bundle_version") != AGENT_BUNDLE_VERSION:
        raise GuardError("baseline SLT version does not match installed guard")

    before = baseline.get("snapshot")
    if not isinstance(before, dict):
        raise GuardError("baseline snapshot is missing or invalid")
    changed = changed_paths(before, snapshot(root))
    allowed = list(contract.get("allowed_files", []))
    shared = list(contract.get("shared_or_generated_files", []))
    forbidden = list(contract.get("forbidden_files", []))

    violations: list[dict[str, str]] = []
    rows: list[dict[str, str]] = []
    for path in changed:
        if matches(path, forbidden):
            status = "FORBIDDEN"
            violations.append({"path": path, "reason": status})
        elif matches(path, allowed):
            status = "ALLOWED"
        elif matches(path, shared):
            status = "DECLARED_SHARED"
        else:
            status = "UNDECLARED"
            violations.append({"path": path, "reason": status})
        rows.append({"path": path, "status": status})

    result = {
        "task_id": contract["id"],
        "contract_hash": contract["contract_hash"],
        "changed": rows,
        "violations": violations,
        "ok": not violations,
    }
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        if not rows:
            print("NO_CHANGES")
        for row in rows:
            print(f"{row['status']:<16} {row['path']}")
        print("PASS" if not violations else "FAIL")
    return 0 if not violations else 3


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    h = sub.add_parser("hash-contract")
    h.add_argument("--contract", required=True)
    h.add_argument("--write", action="store_true")
    h.set_defaults(func=cmd_hash)
    v = sub.add_parser("validate-task-contract")
    v.add_argument("--contract", required=True)
    v.add_argument("--allow-missing-hash", action="store_true")
    v.set_defaults(func=cmd_validate)
    b = sub.add_parser("create-task-baseline")
    b.add_argument("--contract", required=True)
    b.add_argument("--repo")
    b.add_argument("--output")
    b.set_defaults(func=cmd_baseline)
    w = sub.add_parser("verify-write-set")
    w.add_argument("--contract", required=True)
    w.add_argument("--repo")
    w.add_argument("--baseline")
    w.add_argument("--json", action="store_true")
    w.set_defaults(func=cmd_verify)
    return p


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.func(args)
    except GuardError as exc:
        eprint("ERROR:", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
