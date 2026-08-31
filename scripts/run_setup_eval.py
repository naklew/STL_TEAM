#!/usr/bin/env python3
"""Exercise SLT setup/status in a normal checkout and a linked Git worktree."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
SETUP = SCRIPT_DIR / "slt_setup.py"


def run(*args: str, cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(SETUP), *args], cwd=cwd, text=True, capture_output=True)
    if proc.returncode != expect:
        raise RuntimeError(
            f"setup failed: {' '.join(args)} expected={expect} actual={proc.returncode}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="slt-setup-eval-") as td:
        base = Path(td) / "repo"
        worktree = Path(td) / "linked"
        base.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.email", "slt@example.invalid"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.name", "SLT Eval"], cwd=base, check=True)
        (base / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=base, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=base, check=True)
        subprocess.run(["git", "branch", "linked-branch"], cwd=base, check=True)
        subprocess.run(["git", "worktree", "add", "-q", str(worktree), "linked-branch"], cwd=base, check=True)

        # Normal checkout install/status.
        run("install", str(base), cwd=base)
        run("status", str(base), cwd=base)

        # Linked worktree has .git as a file; install must still succeed.
        if not (worktree / ".git").is_file():
            raise RuntimeError("test did not create a linked worktree")
        run("install", str(worktree), cwd=worktree)
        run("status", str(worktree), cwd=worktree)

        exclude = subprocess.check_output(
            ["git", "-C", str(worktree), "rev-parse", "--git-path", "info/exclude"],
            text=True,
        ).strip()
        exclude_path = Path(exclude)
        if not exclude_path.is_absolute():
            exclude_path = worktree / exclude_path
        if ".codex/slt-state/" not in exclude_path.read_text(encoding="utf-8"):
            raise RuntimeError("worktree-local exclude was not updated")

        # Status must detect managed-file drift and recover after update.
        agent = worktree / ".codex" / "agents" / "luna-fast.toml"
        agent.write_text(agent.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
        run("status", str(worktree), cwd=worktree, expect=4)
        run("update", str(worktree), cwd=worktree)
        run("status", str(worktree), cwd=worktree)

        # Status must also detect config drift.
        config = worktree / ".codex" / "config.toml"
        config.write_text("[agents]\nenabled = false\nmax_concurrent_threads_per_session = 9\n", encoding="utf-8")
        run("status", str(worktree), cwd=worktree, expect=4)
        run("update", str(worktree), cwd=worktree)
        run("status", str(worktree), cwd=worktree)

    print("PASS setup/worktree eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
