# SLT Hybrid Cost-Aware Team v0.4.0

A Codex multi-agent orchestration package designed to preserve Sol-level judgment while reducing Sol usage on routine implementation and adding machine-verifiable writer safety.

## Architecture

```text
Terra High parent
  -> semantic classification
  -> deterministic routing policy
     -> Sol Architect High only for unresolved material decisions
     -> Luna High for mechanical bounded work
     -> Luna Max for logic-heavy bounded work
     -> Terra High for complex but already-decided work
  -> workspace-local single-writer lock
  -> contract hash + baseline + parent-held SHA-256 seal
  -> writer execution
  -> tracked/untracked/ignored/case-aware write-set verification
  -> Terra integration
  -> final material review-risk classification
     -> Sol Reviewer High only when required
```

Semantic classification itself remains model/user judgment. After classification, routing, version checks, contract hashes, base-revision checks, writer locking, baseline sealing, and write-set verification are deterministic scripts.

## Install

```bash
git clone https://github.com/naklew/STL_TEAM.git
cd STL_TEAM
codex plugin marketplace add naklew/STL_TEAM --ref main
codex plugin add sol-luna-team@sol-luna-team
python scripts/slt_setup.py install /path/to/target-project
python scripts/slt_setup.py status /path/to/target-project
```

The setup tool supports normal checkouts and linked Git worktrees. Start a new Codex session on `gpt-5.6-terra` with `high` reasoning, then explicitly invoke `$sol-luna-team`.

## Writer guard sequence

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id TASK-001
python .codex/slt-tools/contract_guard.py hash-contract --contract <contract.json> --write
python .codex/slt-tools/contract_guard.py validate-task-contract --contract <contract.json>
python .codex/slt-tools/contract_guard.py create-task-baseline --contract <contract.json> --json
# parent retains baseline_sha256; do not give the seal to the writer
# run named worker
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract <contract.json> \
  --baseline-sha <PARENT_HELD_BASELINE_SHA256>
python .codex/slt-tools/writer_lock.py release --task-id TASK-001
```

The default lock and baseline live under `<worktree>/.codex/slt-state/`, so normal Codex `workspace-write` can create them without writing `.git` or `~/.codex`. Baseline integrity is checked with the parent-held SHA-256 seal.

Ignored untracked files are included by default. The guard also resolves actual filesystem casing so Windows case-only renames are visible. Large disposable trees can be explicitly listed in `snapshot_exclude`; excluded paths are not protected.

## Validation

```bash
python scripts/validate_repo.py
python scripts/run_policy_eval.py
python scripts/run_guard_eval.py
python scripts/run_setup_eval.py
```

GitHub Actions runs the validation matrix on both Ubuntu and Windows.

See [README.DK.md](README.DK.md) for the Korean guide and [INSTALL.txt](INSTALL.txt) for details.
