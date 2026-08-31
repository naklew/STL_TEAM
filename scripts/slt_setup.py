#!/usr/bin/env python3
"""Install or update the SLT agent bundle in a target Codex project.

This manages only SLT-owned custom agents/tools plus the [agents] concurrency keys.
It does not install the Codex plugin itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
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
)
MANIFEST_REL = Path(".codex") / "slt-team.json"
CONFIG_REL = Path(".codex") / "config.toml"
STATE_REL = ".codex/slt-state/"


class SetupError(Exception):
    pass


def load_versions() -> dict[str, str]:
    try:
        data = json.loads(VERSION_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SetupError(f"cannot read {VERSION_FILE}: {exc}") from exc
    required = ("plugin_version", "policy_version", "agent_bundle_version")
    for key in required:
        if not isinstance(data.get(key), str) or not data[key]:
            raise SetupError(f"{VERSION_FILE} missing {key}")
    return data


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_sources() -> None:
    for name in MANAGED_AGENT_FILES:
        if not (AGENT_SOURCE / name).is_file():
            raise SetupError(f"missing agent source: {AGENT_SOURCE / name}")
    for name in MANAGED_TOOL_FILES:
        if not (TOOL_SOURCE / name).is_file():
            raise SetupError(f"missing tool source: {TOOL_SOURCE / name}")


def merge_agents_config(path: Path) -> None:
    """Preserve existing TOML text while setting two keys in [agents]."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = ""

    lines = text.splitlines()
    section_start = None
    section_end = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "[agents]":
            section_start = i
            break
    if section_start is not None:
        section_end = len(lines)
        for i in range(section_start + 1, len(lines)):
            stripped = lines[i].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_end = i
                break

        keys = {
            "enabled": "enabled = true",
            "max_concurrent_threads_per_session": "max_concurrent_threads_per_session = 2",
        }
        found: set[str] = set()
        for i in range(section_start + 1, section_end):
            stripped = lines[i].strip()
            for key, replacement in keys.items():
                if stripped.startswith(key) and "=" in stripped:
                    lines[i] = replacement
                    found.add(key)
        insert_at = section_end
        for key, replacement in keys.items():
            if key not in found:
                lines.insert(insert_at, replacement)
                insert_at += 1
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines += [
            "[agents]",
            "enabled = true",
            "max_concurrent_threads_per_session = 2",
        ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def git_root(target: Path) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    return Path(proc.stdout.strip()).resolve()


def ensure_local_exclude(target: Path) -> None:
    root = git_root(target)
    if root is None:
        return
    exclude = root / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = existing.splitlines()
    if STATE_REL not in [line.strip() for line in lines]:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("# SLT local runtime state")
        lines.append(STATE_REL)
        exclude.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


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


def install_bundle(target: Path, *, update: bool, force: bool, dry_run: bool) -> int:
    ensure_sources()
    versions = load_versions()
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)

    existing_manifest = read_manifest(target)
    if update and existing_manifest is None and not force:
        raise SetupError("update requested but .codex/slt-team.json is missing; use install or --force")

    managed = expected_managed_files()
    conflicts: list[str] = []
    if not update and not force:
        for rel in managed:
            if (target / rel).exists():
                conflicts.append(rel)
        if conflicts:
            raise SetupError(
                "managed files already exist; refusing to overwrite without --force: "
                + ", ".join(conflicts)
            )

    if dry_run:
        print(f"TARGET {target}")
        for rel in managed:
            print(("UPDATE " if (target / rel).exists() else "CREATE ") + rel)
        print("MERGE  " + str(CONFIG_REL))
        print("WRITE  " + str(MANIFEST_REL))
        return 0

    for rel, src in managed.items():
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    merge_agents_config(target / CONFIG_REL)
    ensure_local_exclude(target)

    manifest = {
        "format_version": 1,
        **versions,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "managed_files": {
            rel: {
                "sha256": sha256_file(src),
            }
            for rel, src in managed.items()
        },
    }
    manifest_path = target / MANIFEST_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"SLT bundle {versions['agent_bundle_version']} installed in {target}")
    return 0


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
        if state != "OK":
            ok = False
        print(f"{key}: installed={installed} current={current} {state}")

    managed = expected_managed_files()
    for rel, src in managed.items():
        dst = target / rel
        if not dst.exists():
            print(f"MISSING {rel}")
            ok = False
            continue
        expected = sha256_file(src)
        actual = sha256_file(dst)
        if expected == actual:
            print(f"OK      {rel}")
        else:
            print(f"DRIFT   {rel}")
            ok = False

    return 0 if ok else 4


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)

    for command in ("install", "update"):
        sp = sub.add_parser(command)
        sp.add_argument("target", help="target project root")
        sp.add_argument("--force", action="store_true")
        sp.add_argument("--dry-run", action="store_true")

    st = sub.add_parser("status")
    st.add_argument("target", help="target project root")
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
