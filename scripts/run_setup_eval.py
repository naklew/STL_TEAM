#!/usr/bin/env python3
"""Exercise SLT setup/status, rollback, and linked Git worktree support."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile

SCRIPT_DIR = Path(__file__).resolve().parent
SETUP = SCRIPT_DIR / "slt_setup.py"
sys.path.insert(0, str(SCRIPT_DIR))
import slt_setup as setup_mod  # noqa: E402


def run(*args: str, cwd: Path, expect: int = 0) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(SETUP), *args], cwd=cwd, text=True, capture_output=True)
    if proc.returncode != expect:
        raise RuntimeError(
            f"setup failed: {' '.join(args)} expected={expect} actual={proc.returncode}\n"
            f"stdout={proc.stdout}\nstderr={proc.stderr}"
        )
    return proc


def capture(paths: list[Path]) -> dict[Path, bytes | None]:
    return {p: p.read_bytes() if p.exists() else None for p in paths}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="slt-setup-eval-") as td:
        base = Path(td) / "repo"
        worktree = Path(td) / "linked"
        rollback_wt = Path(td) / "rollback"
        base.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.email", "slt@example.invalid"], cwd=base, check=True)
        subprocess.run(["git", "config", "user.name", "SLT Eval"], cwd=base, check=True)
        (base / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=base, check=True)
        subprocess.run(["git", "commit", "-qm", "base"], cwd=base, check=True)
        subprocess.run(["git", "branch", "linked-branch"], cwd=base, check=True)
        subprocess.run(["git", "branch", "rollback-branch"], cwd=base, check=True)
        subprocess.run(["git", "worktree", "add", "-q", str(worktree), "linked-branch"], cwd=base, check=True)
        subprocess.run(["git", "worktree", "add", "-q", str(rollback_wt), "rollback-branch"], cwd=base, check=True)

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
            raise RuntimeError("worktree-safe exclude was not updated")

        # Status detects managed-file drift and update repairs it.
        agent = worktree / ".codex" / "agents" / "luna-fast.toml"
        agent.write_text(agent.read_text(encoding="utf-8") + "# drift\n", encoding="utf-8")
        run("status", str(worktree), cwd=worktree, expect=4)
        run("update", str(worktree), cwd=worktree)
        run("status", str(worktree), cwd=worktree)

        # Status detects config drift and update repairs it.
        config = worktree / ".codex" / "config.toml"
        config.write_text("[agents]\nenabled = false\nmax_concurrent_threads_per_session = 9\n", encoding="utf-8")
        run("status", str(worktree), cwd=worktree, expect=4)
        run("update", str(worktree), cwd=worktree)
        run("status", str(worktree), cwd=worktree)

        # Transaction rollback: inject one mid-apply failure, then allow restore writes.
        run("install", str(rollback_wt), cwd=rollback_wt)
        drift = rollback_wt / ".codex" / "agents" / "luna-fast.toml"
        drift.write_text(drift.read_text(encoding="utf-8") + "# preserve-this-drift\n", encoding="utf-8")
        root = setup_mod.git_root(rollback_wt)
        rollback_exclude = setup_mod.git_path(root, "info/exclude") if root else None
        tracked_paths = [rollback_wt / rel for rel in setup_mod.expected_managed_files()]
        tracked_paths += [rollback_wt / setup_mod.CONFIG_REL, rollback_wt / setup_mod.MANIFEST_REL]
        if rollback_exclude:
            tracked_paths.append(rollback_exclude)
        before = capture(tracked_paths)

        original_atomic = setup_mod.atomic_write
        calls = {"n": 0, "failed": False}

        def flaky_atomic(path: Path, data: bytes) -> None:
            calls["n"] += 1
            if calls["n"] == 2 and not calls["failed"]:
                calls["failed"] = True
                raise OSError("injected setup failure")
            original_atomic(path, data)

        setup_mod.atomic_write = flaky_atomic
        try:
            try:
                setup_mod.install_bundle(rollback_wt, update=True, force=False, dry_run=False)
            except setup_mod.SetupError:
                pass
            else:
                raise RuntimeError("injected setup failure did not fail update")
        finally:
            setup_mod.atomic_write = original_atomic

        after = capture(tracked_paths)
        if after != before:
            changed = [str(p) for p in tracked_paths if before[p] != after[p]]
            raise RuntimeError(f"rollback left partial changes: {changed}")

    print("PASS setup/worktree/rollback eval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
