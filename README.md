# SLT Hybrid Cost-Aware Team v0.3.0

A Codex multi-agent orchestration package designed to preserve Sol-level judgment while reducing
Sol usage on routine implementation.

## Architecture

```text
Terra High parent
  -> semantic classification
  -> deterministic routing policy
     -> Sol Architect High only for unresolved material decisions
     -> Luna High for mechanical bounded work
     -> Luna Max for logic-heavy bounded work
     -> Terra High for complex but already-decided work
  -> deterministic write-set verification
  -> Terra integration
  -> final review-risk classification
     -> Sol Reviewer High only when required
```

The semantic classification itself is still model/user judgment. The repository makes the steps
after classification deterministic: versioned routing, contract hashing, baseline snapshots,
write-set checks, package validation, and scenario evals.

## Install

```bash
git clone https://github.com/naklew/STL_TEAM.git
cd STL_TEAM
codex plugin marketplace add naklew/STL_TEAM --ref main
codex plugin add sol-luna-team@sol-luna-team
python scripts/slt_setup.py install /path/to/target-project
```

Start a new Codex session on `gpt-5.6-terra` with `high` reasoning, then explicitly invoke
`$sol-luna-team`.

Check/update the project agent bundle:

```bash
python scripts/slt_setup.py status /path/to/target-project
python scripts/slt_setup.py update /path/to/target-project
```

## Validation

```bash
python scripts/validate_repo.py
python scripts/run_policy_eval.py
python scripts/run_guard_eval.py
```

See [README.DK.md](README.DK.md) for the Korean guide and [INSTALL.txt](INSTALL.txt) for details.
