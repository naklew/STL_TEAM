#!/usr/bin/env python3
"""Install, update, and verify the SLT agent bundle in a Codex project.

v0.4.0 is worktree-safe and transactional for project files. It resolves Git's
actual info/exclude path with `git rev-parse --git-path`, stages all generated
content before applying it, and restores previous project/exclude content if an
apply step fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = PACKAGE_ROOT / "slt-version.json"
AGENT_SOURCE = PACKAGE_ROOT / "templates" / "project" / ".codex" / "agents"
TOOL_SOURCE = PACKAGE_ROOT / "scripts"

MANAGED_AGENT_FILES = (
    "luna-fast.toml",
    "luna-worker.toml",
    "terra-worker.toml",
    "sol-architect.toml",
    "sol-reviewer.toml",
)
MANAGED_TOOL_FILES = (
    "contract_guard.py",
    "routing_policy.py",
    "writer_lock.py",
)
MANIFEST_REL = Path(".codex") / "slt-team.json"
CONFIG_REL = Path(".codex") / "config.toml"
STATE_EXCLUDE = ".codex/slt-state/"


class SetupError(Exception):
    pass


def load_versions() -> dict[str, str]:
    try:
        data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"cannot read {VERSION_FILE}: {exc}") from exc
    for key in ("plugin_version", "policy_version", "agent_bundle_version"):
        if not isinstance(data.get(key), str) or not data[key]:
            raise SetupError(f"{VERSION_FILE} missing {key}")
    return data


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def ensure_sources() -> None:
    for name in MANAGED_AGENT_FILES:
        if not (AGENT_SOURCE / name).is_file():
            raise SetupError(f"missing agent source: {AGENT_SOURCE / name}")
    for name in MANAGED_TOOL_FILES:
        if not (TOOL_SOURCE / name).is_file():
            raise SetupError(f"missing tool source: {TOOL_SOURCE / name}")


def render_agents_config(text: str) -> str:
    """Preserve arbitrary TOML text while enforcing SLT's [agents] keys."""
    lines = text.splitlines()
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        if line.strip() == "[agents]":
            section_start = i
            break
    if section_start is not None:
        section_end = len(lines)
        for i in range(section_start + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_end = i
                break
        required = {
            "enabled": "enabled = true",
            "max_concurrent_threads_per_session": "max_concurrent_threads_per_session = 2",
        }
        found: set[str] = set()
        for i in range(section_start + 1, section_end):
            stripped = lines[i].strip()
            for key, replacement in required.items():
                if stripped.startswith(key) and "=" in stripped:
                    lines[i] = replacement
                    found.add(key)
        insert_at = section_end
        for key, replacement in required.items():
            if key not in found:
                lines.insert(insert_at, replacement)
                insert_at += 1
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines += ["[agents]", "enabled = true", "max_concurrent_threads_per_session = 2"]
    return "\n".join(lines).rstrip() + "\n"


def git_root(target: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def git_path(root: Path, rel: str) -> Path:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", rel],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise SetupError(f"cannot resolve git path {rel}: {proc.stderr.strip()}")
    path = Path(proc.stdout.strip())
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def render_local_exclude(existing: str) -> str:
    lines = existing.splitlines()
    normalized = {line.strip() for line in lines}
    if STATE_EXCLUDE not in normalized:
        if lines and lines[-1].strip():
            lines.append("")
        lines += ["# SLT local runtime state", STATE_EXCLUDE]
    return "\n".join(lines).rstrip() + "\n"


def expected_managed_files() -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name in MANAGED_AGENT_FILES:
        result[str(Path(".codex") / "agents" / name)] = AGENT_SOURCE / name
    for name in MANAGED_TOOL_FILES:
        result[str(Path(".codex") / "slt-tools" / name)] = TOOL_SOURCE / name
    return result


def read_manifest(target: Path) -> dict[str, Any] | None:
    path = target / MANIFEST_REL
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.slt-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def snapshot_paths(paths: list[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def restore_paths(snapshot: dict[Path, bytes | None]) -> None:
    for path, data in snapshot.items():
        try:
            if data is None:
                if path.exists():
                    path.unlink()
            else:
                atomic_write(path, data)
        except OSError:
            # Best-effort rollback: preserve the original exception from install.
            pass


def build_manifest(versions: dict[str, str], managed: dict[str, Path]) -> dict[str, Any]:
    return {
        "format_version": 2,
        **versions,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "managed_files": {rel: {"sha256": sha256_file(src)} for rel, src in managed.items()},
    }


def install_bundle(target: Path, *, update: bool, force: bool, dry_run: bool) -> int:
    ensure_sources()
    versions = load_versions()
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    existing_manifest = read_manifest(target)
    if update and existing_manifest is None and not force:
        raise SetupError("update requested but .codex/slt-team.json is missing; use install or --force")

    managed = expected_managed_files()
    if not update and not force:
        conflicts = [rel for rel in managed if (target / rel).exists()]
        if conflicts:
            raise SetupError("managed files already exist; use --force: " + ", ".join(conflicts))

    root = git_root(target)
    exclude_path = git_path(root, "info/exclude") if root is not None else None
    old_config = (target / CONFIG_REL).read_text(encoding="utf-8") if (target / CONFIG_REL).exists() else ""
    new_config = render_agents_config(old_config)
    old_exclude = exclude_path.read_text(encoding="utf-8") if exclude_path and exclude_path.exists() else ""
    new_exclude = render_local_exclude(old_exclude) if exclude_path else None
    manifest_bytes = (json.dumps(build_manifest(versions, managed), indent=2, sort_keys=True) + "\n").encode()

    if dry_run:
        print(f"TARGET {target}")
        print(f"GIT_MODE {'worktree-aware' if root else 'not-a-git-worktree'}")
        for rel in managed:
            print(("UPDATE " if (target / rel).exists() else "CREATE ") + rel)
        print("MERGE  " + str(CONFIG_REL))
        print("WRITE  " + str(MANIFEST_REL))
        if exclude_path:
            print("MERGE  " + str(exclude_path))
        return 0

    # Stage every package-owned file first so source/read errors cannot leave a partial install.
    staged: dict[Path, bytes] = {}
    for rel, src in managed.items():
        staged[target / rel] = src.read_bytes()
    staged[target / CONFIG_REL] = new_config.encode("utf-8")
    staged[target / MANIFEST_REL] = manifest_bytes
    if exclude_path and new_exclude is not None:
        staged[exclude_path] = new_exclude.encode("utf-8")

    originals = snapshot_paths(list(staged))
    try:
        for path, data in staged.items():
            atomic_write(path, data)
    except Exception as exc:
        restore_paths(originals)
        raise SetupError(f"install failed and rollback was attempted: {exc}") from exc

    print(f"SLT bundle {versions['agent_bundle_version']} installed in {target}")
    return 0


def check_config(path: Path) -> tuple[bool, str]:
    if not path.exists():
        return False, "MISSING config.toml"
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return False, f"INVALID config.toml: {exc}"
    agents = data.get("agents", {})
    ok = agents.get("enabled") is True and agents.get("max_concurrent_threads_per_session") == 2
    ok = ok and "default_subagent_model" not in agents
    return ok, "OK config.toml" if ok else "DRIFT config.toml [agents]"


def status(target: Path) -> int:
    ensure_sources()
    target = target.resolve()
    versions = load_versions()
    manifest = read_manifest(target)
    if manifest is None:
        print("NOT_INSTALLED")
        return 3

    ok = True
    print(f"target: {target}")
    for key in ("plugin_version", "policy_version", "agent_bundle_version"):
        installed = manifest.get(key)
        current = versions[key]
        state = "OK" if installed == current else "OUTDATED"
        ok &= state == "OK"
        print(f"{key}: installed={installed} current={current} {state}")

    for rel, src in expected_managed_files().items():
        dst = target / rel
        if not dst.exists():
            print(f"MISSING {rel}")
            ok = False
        elif sha256_file(dst) != sha256_file(src):
            print(f"DRIFT   {rel}")
            ok = False
        else:
            print(f"OK      {rel}")

    config_ok, config_msg = check_config(target / CONFIG_REL)
    print(config_msg)
    ok &= config_ok

    root = git_root(target)
    if root is not None:
        try:
            exclude = git_path(root, "info/exclude")
            text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
            exclude_ok = STATE_EXCLUDE in {line.strip() for line in text.splitlines()}
            print(("OK      " if exclude_ok else "MISSING ") + f"git exclude {exclude}")
            ok &= exclude_ok
        except SetupError as exc:
            print(f"ERROR   git exclude: {exc}")
            ok = False

    return 0 if ok else 4


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("install", "update"):
        sp = sub.add_parser(command)
        sp.add_argument("target")
        sp.add_argument("--force", action="store_true")
        sp.add_argument("--dry-run", action="store_true")
    st = sub.add_parser("status")
    st.add_argument("target")
    return p


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "install":
            return install_bundle(Path(args.target), update=False, force=args.force, dry_run=args.dry_run)
        if args.command == "update":
            return install_bundle(Path(args.target), update=True, force=args.force, dry_run=args.dry_run)
        return status(Path(args.target))
    except SetupError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
