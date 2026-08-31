#!/usr/bin/env python3
"""Machine-verifiable SLT task contracts and write-set guard.

SLT v0.4 hotfix behavior:
- tracked, non-ignored untracked, and ignored untracked files are snapshotted;
- actual filesystem casing is preserved so case-only renames are visible on Windows;
- runtime state defaults to <worktree>/.codex/slt-state, writable under Codex workspace-write;
- baseline integrity is protected by a parent-held SHA-256 seal required at verification time;
- base_revision must match HEAD and HEAD must remain unchanged;
- a matching worktree-scoped writer lock is required.

Semantic risk classification remains model/user judgment. This tool enforces
what can be made deterministic after a contract exists.
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

from policy_defs import (
    AGENT_BUNDLE_VERSION,
    BOUNDED_REASONING,
    DECISION_FLAGS,
    POLICY_VERSION,
    REVIEW_FLAGS,
    TASK_CLASSES,
)

REQUIRED_FIELDS = (
    "id", "policy_version", "agent_bundle_version", "base_revision", "goal",
    "context", "read_scope", "allowed_files", "forbidden_files",
    "shared_or_generated_files", "snapshot_exclude", "acceptance_criteria",
    "verification", "integration_verification", "dependencies", "execution",
    "decision_gate", "review_risk", "escalation_conditions",
)
LIST_FIELDS = (
    "context", "read_scope", "allowed_files", "forbidden_files",
    "shared_or_generated_files", "snapshot_exclude", "acceptance_criteria",
    "verification", "integration_verification", "dependencies", "escalation_conditions",
)
RUNTIME_EXCLUDES = (".codex/slt-state/**",)


class GuardError(Exception):
    pass


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError(f"file not found: {path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise GuardError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise GuardError(f"expected JSON object in {path}")
    return data


def save_json(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        raise GuardError(f"cannot write {path}: {exc}") from exc


def canonical_contract(contract: dict[str, Any]) -> bytes:
    material = {k: v for k, v in contract.items() if k != "contract_hash"}
    return json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def compute_contract_hash(contract: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(canonical_contract(contract)).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise GuardError(f"cannot hash {path}: {exc}") from exc
    return "sha256:" + h.hexdigest()


def validate_bool_map(name: str, value: Any, expected_keys: tuple[str, ...]) -> list[str]:
    if not isinstance(value, dict):
        return [f"{name} must be an object"]
    errors: list[str] = []
    expected, actual = set(expected_keys), set(value)
    if expected - actual:
        errors.append(f"{name} missing keys: {', '.join(sorted(expected - actual))}")
    if actual - expected:
        errors.append(f"{name} has unknown keys: {', '.join(sorted(actual - expected))}")
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
    for field in ("read_scope", "allowed_files", "forbidden_files", "shared_or_generated_files", "snapshot_exclude"):
        if isinstance(contract.get(field), list):
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
        if task_class not in TASK_CLASSES:
            errors.append("execution.task_class must be trivial|bounded|complex_decided")
        reasoning = execution.get("bounded_reasoning")
        if task_class == "bounded" and reasoning not in BOUNDED_REASONING:
            errors.append("bounded execution requires bounded_reasoning=mechanical|logic")
        if task_class != "bounded" and reasoning not in (None, ""):
            errors.append("bounded_reasoning is only valid for bounded tasks")

    errors.extend(validate_bool_map("decision_gate", contract.get("decision_gate"), DECISION_FLAGS))
    errors.extend(validate_bool_map("review_risk", contract.get("review_risk"), REVIEW_FLAGS))

    allowed = set(contract.get("allowed_files", [])) if isinstance(contract.get("allowed_files"), list) else set()
    forbidden = set(contract.get("forbidden_files", [])) if isinstance(contract.get("forbidden_files"), list) else set()
    overlap = sorted(allowed & forbidden)
    if overlap:
        errors.append("paths cannot be both allowed and forbidden: " + ", ".join(overlap))

    if require_hash:
        actual, expected = contract.get("contract_hash"), compute_contract_hash(contract)
        if not isinstance(actual, str) or not actual:
            errors.append("missing contract_hash")
        elif actual != expected:
            errors.append(f"contract_hash mismatch: expected {expected}, got {actual}")
    return errors


def git_root(start: Path | None = None) -> Path:
    proc = subprocess.run(["git", "-C", str(start or Path.cwd()), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise GuardError("not inside a Git worktree")
    return Path(proc.stdout.strip()).resolve()


def git_head(root: Path) -> str:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else "UNBORN"


def run_ls(root: Path, args: list[str]) -> set[str]:
    proc = subprocess.run(["git", "-C", str(root), "ls-files", *args, "-z"], capture_output=True)
    if proc.returncode != 0:
        raise GuardError(proc.stderr.decode("utf-8", errors="replace").strip() or "git ls-files failed")
    result: set[str] = set()
    for item in proc.stdout.split(b"\0"):
        if item:
            result.add(item.decode("utf-8", errors="surrogateescape").replace(os.sep, "/"))
    return result


def matches(path: str, patterns: list[str] | tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _dir_case_maps(directory: Path, cache: dict[str, tuple[dict[str, str], dict[str, list[str]]]]) -> tuple[dict[str, str], dict[str, list[str]]]:
    key = str(directory)
    if key in cache:
        return cache[key]
    exact: dict[str, str] = {}
    folded: dict[str, list[str]] = {}
    try:
        with os.scandir(directory) as entries:
            for entry in entries:
                exact[entry.name] = entry.name
                folded.setdefault(entry.name.casefold(), []).append(entry.name)
    except OSError:
        pass
    cache[key] = (exact, folded)
    return exact, folded


def actual_case_rel(root: Path, rel: str, cache: dict[str, tuple[dict[str, str], dict[str, list[str]]]]) -> str:
    """Return actual directory-entry casing for a Git-reported path."""
    current = root
    actual_parts: list[str] = []
    for part in rel.replace("\\", "/").split("/"):
        if not part:
            continue
        exact, folded = _dir_case_maps(current, cache)
        if part in exact:
            chosen = part
        else:
            candidates = folded.get(part.casefold(), [])
            chosen = candidates[0] if len(candidates) == 1 else part
        actual_parts.append(chosen)
        current = current / chosen
    return "/".join(actual_parts)


def worktree_paths(root: Path, snapshot_exclude: list[str]) -> list[str]:
    raw = run_ls(root, ["-c"])
    raw |= run_ls(root, ["-o", "--exclude-standard"])
    raw |= run_ls(root, ["-o", "-i", "--exclude-standard"])
    cache: dict[str, tuple[dict[str, str], dict[str, list[str]]]] = {}
    exclusions = list(RUNTIME_EXCLUDES) + snapshot_exclude
    paths: set[str] = set()
    for rel in raw:
        actual = actual_case_rel(root, rel, cache)
        if not matches(actual, exclusions):
            paths.add(actual)
    return sorted(paths)


def hash_path(path: Path) -> str:
    if path.is_symlink():
        try:
            target = os.readlink(path)
        except OSError as exc:
            raise GuardError(f"cannot read symlink {path}: {exc}") from exc
        return hashlib.sha256(("SYMLINK\0" + target).encode("utf-8", errors="surrogateescape")).hexdigest()
    h = hashlib.sha256()
    try:
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
    except OSError as exc:
        raise GuardError(f"cannot hash worktree path {path}: {exc}") from exc
    return h.hexdigest()


def snapshot(root: Path, snapshot_exclude: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel in worktree_paths(root, snapshot_exclude):
        p = root / Path(rel.replace("/", os.sep))
        if p.is_file() or p.is_symlink():
            result[rel] = hash_path(p)
    return result


def changed_paths(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def safe_task_id(task_id: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in task_id)


def worktree_identity(root: Path) -> str:
    return hashlib.sha256(str(root.resolve()).encode("utf-8", errors="surrogateescape")).hexdigest()[:24]


def state_root(root: Path) -> Path:
    configured = os.environ.get("SLT_STATE_HOME")
    if configured:
        base = Path(configured).expanduser()
        if not base.is_absolute():
            base = root / base
        path = base / "worktrees" / worktree_identity(root)
    else:
        path = root / ".codex" / "slt-state"
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GuardError(f"cannot create SLT runtime state at {path}: {exc}. Use a writable workspace path or set SLT_STATE_HOME explicitly.") from exc
    return path.resolve()


def default_baseline_path(root: Path, task_id: str) -> Path:
    path = state_root(root) / "baselines" / f"{safe_task_id(task_id)}.baseline.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GuardError(f"cannot create baseline directory {path.parent}: {exc}") from exc
    return path


def writer_lock_path(root: Path) -> Path:
    path = state_root(root) / "locks" / "slt-writer.lock"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GuardError(f"cannot create lock directory {path.parent}: {exc}") from exc
    return path


def writer_lock(root: Path) -> dict[str, Any] | None:
    path = writer_lock_path(root)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise GuardError(f"invalid writer lock {path}: {exc}") from exc
    return data if isinstance(data, dict) else None


def require_writer_lock(root: Path, task_id: str) -> None:
    lock = writer_lock(root)
    if not lock or lock.get("task_id") != task_id:
        raise GuardError(f"writer lock for task {task_id} is required")


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
    current_head = git_head(root)
    if contract["base_revision"] != current_head:
        raise GuardError(f"base_revision {contract['base_revision']} does not match HEAD {current_head}")
    require_writer_lock(root, contract["id"])
    baseline = {
        "format_version": 3,
        "task_id": contract["id"],
        "contract_hash": contract["contract_hash"],
        "policy_version": POLICY_VERSION,
        "agent_bundle_version": AGENT_BUNDLE_VERSION,
        "git_head": current_head,
        "snapshot_exclude": contract["snapshot_exclude"],
        "snapshot": snapshot(root, contract["snapshot_exclude"]),
    }
    out = Path(args.output).resolve() if args.output else default_baseline_path(root, contract["id"])
    save_json(out, baseline)
    seal = sha256_file(out)
    payload = {"baseline": str(out), "baseline_sha256": seal}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print(f"BASELINE {out}")
        print(f"BASELINE_SHA256 {seal}")
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
    require_writer_lock(root, contract["id"])
    baseline_path = Path(args.baseline).resolve() if args.baseline else default_baseline_path(root, contract["id"])
    actual_baseline_sha = sha256_file(baseline_path)
    if actual_baseline_sha != args.baseline_sha:
        raise GuardError(f"baseline SHA mismatch: expected {args.baseline_sha}, got {actual_baseline_sha}")
    baseline = load_json(baseline_path)
    if baseline.get("task_id") != contract["id"]:
        raise GuardError("baseline task_id does not match contract")
    if baseline.get("contract_hash") != contract["contract_hash"]:
        raise GuardError("baseline contract_hash does not match current contract")
    if baseline.get("policy_version") != POLICY_VERSION or baseline.get("agent_bundle_version") != AGENT_BUNDLE_VERSION:
        raise GuardError("baseline SLT version does not match installed guard")
    if baseline.get("git_head") != contract["base_revision"]:
        raise GuardError("baseline git_head does not match contract base_revision")
    if git_head(root) != baseline.get("git_head"):
        raise GuardError("HEAD changed after baseline creation")
    if baseline.get("snapshot_exclude") != contract.get("snapshot_exclude"):
        raise GuardError("snapshot_exclude changed after baseline creation")
    before = baseline.get("snapshot")
    if not isinstance(before, dict):
        raise GuardError("baseline snapshot is missing or invalid")
    changed = changed_paths(before, snapshot(root, contract["snapshot_exclude"]))
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
        "baseline_sha256": args.baseline_sha,
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
    b.add_argument("--json", action="store_true")
    b.set_defaults(func=cmd_baseline)
    w = sub.add_parser("verify-write-set")
    w.add_argument("--contract", required=True)
    w.add_argument("--repo")
    w.add_argument("--baseline")
    w.add_argument("--baseline-sha", required=True)
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
