#!/usr/bin/env python3
"""Single-writer lock for SLT shared-workspace execution.

The lock lives in the current Git worktree's private gitdir (resolved with
`git rev-parse --git-path`), so two writers cannot be active in the same
worktree while independent Git worktrees can proceed separately.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

LOCK_NAME = "slt-writer.lock"


class LockError(Exception):
    pass


def git_root(start: Path | None = None) -> Path:
    cwd = str(start or Path.cwd())
    proc = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise LockError("not inside a Git worktree")
    return Path(proc.stdout.strip()).resolve()


def git_path(root: Path, rel: str) -> Path:
    proc = subprocess.run(["git", "-C", str(root), "rev-parse", "--git-path", rel], capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        raise LockError(f"cannot resolve git path {rel}: {proc.stderr.strip()}")
    path = Path(proc.stdout.strip())
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def lock_path(root: Path) -> Path:
    return git_path(root, LOCK_NAME)


def read_lock(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise LockError(f"invalid writer lock {path}: {exc}") from exc
    return data if isinstance(data, dict) else None


def acquire(root: Path, task_id: str) -> int:
    path = lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "worktree": str(root),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creator_pid": os.getpid(),
    }
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        current = read_lock(path)
        print(f"LOCKED {json.dumps(current, sort_keys=True)}", file=sys.stderr)
        return 3
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"ACQUIRED {task_id} {path}")
    return 0


def release(root: Path, task_id: str, force: bool) -> int:
    path = lock_path(root)
    current = read_lock(path)
    if current is None:
        print("UNLOCKED")
        return 0
    if not force and current.get("task_id") != task_id:
        print(f"REFUSED lock belongs to {current.get('task_id')}", file=sys.stderr)
        return 4
    path.unlink()
    print(f"RELEASED {task_id}")
    return 0


def status(root: Path) -> int:
    path = lock_path(root)
    current = read_lock(path)
    if current is None:
        print("UNLOCKED")
        return 0
    print(json.dumps(current, indent=2, sort_keys=True))
    return 3


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo")
    sub = p.add_subparsers(dest="command", required=True)
    a = sub.add_parser("acquire")
    a.add_argument("--task-id", required=True)
    r = sub.add_parser("release")
    r.add_argument("--task-id", required=True)
    r.add_argument("--force", action="store_true")
    sub.add_parser("status")
    args = p.parse_args()
    try:
        root = git_root(Path(args.repo) if args.repo else None)
        if args.command == "acquire":
            return acquire(root, args.task_id)
        if args.command == "release":
            return release(root, args.task_id, args.force)
        return status(root)
    except LockError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
