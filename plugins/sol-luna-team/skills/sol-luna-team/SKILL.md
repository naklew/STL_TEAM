---
name: sol-luna-team
description: "SLT Hybrid v0.4.0: Terra High parent orchestration with versioned named agents, structured semantic classification, deterministic post-classification routing, worktree-safe setup, protected baselines, ignored-file write-set checks, and worktree-scoped single-writer locking."
---

# SLT Hybrid v0.4.0

Use this skill for authorized implementation, debugging, refactoring, and test work when Sol-level
judgment is valuable but Sol should not spend tokens on routine exploration and coding.

## Objective and honesty boundary

Optimize for **Sol tokens + avoidable rework**, not minimum total tokens.

This package separates semantic judgment from machine enforcement:

1. **Semantic classification remains model/user judgment.** Terra evaluates evidence and marks
   `decision_gate`, `review_risk`, execution class, and any explicit snapshot exclusions.
2. **After classification, routing, version checks, contract hashing, base-revision checks, writer
   locking, baseline capture, and write-set verification are deterministic scripts.**

Do not describe the semantic classifier as code-enforced or fully deterministic. The package is a
policy-guided orchestrator with deterministic guards around the parts that can be mechanically
verified.

## Required parent and bundle preflight

Recommended parent session:
- model: `gpt-5.6-terra`
- reasoning: `high`

The skill cannot switch the parent model. If the current parent is not known to be Terra High,
state that limitation before non-trivial delegation.

Before spawning named workers, run the package readiness check from the checked-out SLT source:

```bash
python scripts/slt_setup.py status <target-project>
```

The command must return success. It verifies:
- `policy_version`, `agent_bundle_version`, and plugin bundle version alignment;
- hashes of managed named-agent and SLT tool files;
- project `.codex/config.toml` agent settings;
- worktree-safe Git `info/exclude` configuration.

The target project must contain these managed tools/agents after setup:
- `.codex/agents/luna-fast.toml`
- `.codex/agents/luna-worker.toml`
- `.codex/agents/terra-worker.toml`
- `.codex/agents/sol-architect.toml`
- `.codex/agents/sol-reviewer.toml`
- `.codex/slt-tools/policy_defs.py`
- `.codex/slt-tools/routing_policy.py`
- `.codex/slt-tools/contract_guard.py`
- `.codex/slt-tools/writer_lock.py`

The manifest must report `policy_version = 0.4.0` and `agent_bundle_version = 0.4.0`.
If status fails, do not silently delegate with guessed/stale models. Update the bundle or continue
only in an explicit single-parent safe mode.

Do not use a child orchestrator. The Terra parent follows this skill directly.
Never invoke Sol Max automatically. Sol Max requires an unresolved high-impact decision after
Sol High plus explicit user approval.

## Roles

| Work | Agent | Model / effort |
| --- | --- | --- |
| Parent orchestration, reconnaissance, integration, verification | parent | Terra High |
| Mechanical bounded implementation | `luna_fast` | Luna High |
| Logic-heavy bounded implementation | `luna_worker` | Luna Max |
| Complex but already-decided multi-file implementation | `terra_worker` | Terra High |
| Unresolved material decision gate | `sol_architect` | Sol High |
| Final material-risk review | `sol_reviewer` | Sol High |

## 1. Trivial fast path

Do not create a team for an obviously trivial change. The Terra parent may edit directly when all
of the following hold:
- at most one or two narrowly scoped files are expected;
- acceptance criteria are explicit;
- no unresolved decision-gate flag is true;
- no material review-risk domain is expected to be touched;
- no new dependency, migration, generated/shared release artifact, security boundary, domain-
  critical logic, deployment/runtime safety, or public contract is involved;
- verification is obvious and local.

After the direct edit, inspect the diff and run relevant verification. If the task stops being
trivial, enter the normal workflow instead of stretching the fast path.

## 2. Reconnaissance and semantic classification

Terra inspects repository instructions, current diff, relevant modules/contracts/tests,
shared/generated artifacts, ignored-but-material local files, and verification commands. Preserve
pre-existing user changes and record observed facts with file/symbol or command evidence.

Create a routing classification JSON under `.codex/slt-state/`. The exact flag names are defined
in `.codex/slt-tools/policy_defs.py` and validated by `routing_policy.py`.

### Decision-gate concepts

Set a `decision_gate` flag when a material question is unresolved, including:
- architecture or acceptance criteria;
- competing root causes;
- contract expansion;
- security/auth policy or broader security/trust-boundary semantics;
- external contract compatibility;
- migration strategy;
- data-integrity/loss semantics;
- project-defined domain-critical behavior;
- concurrency/transaction/idempotency/ordering semantics;
- deployment/runtime safety;
- resource/capacity semantics;
- irreversible/destructive behavior;
- repeated failure.

Any true decision flag requires `sol_architect` before implementation continues.

### Review-risk concepts and materiality

Set a `review_risk` flag when the actual implementation materially touches:
- a public contract/API compatibility boundary;
- schema/migration behavior;
- auth/permission behavior;
- a security/trust boundary, secret handling, deserialization, SSRF/network trust, cryptography,
  or other sensitive input/data-flow boundary;
- data integrity or data-loss risk;
- project-specific financial, numerical, safety, or other domain-critical algorithms;
- concurrency/transaction behavior;
- irreversible operations;
- a materially new/changed dependency or protocol;
- deployment/runtime safety;
- resource exhaustion or capacity safety;
- weak test oracles;
- material generated/shared release artifacts;
- repeated/flaky failure evidence.

The exact v0.4 review-risk keys include `security_boundary_touched`,
`data_integrity_or_loss_risk`, `domain_critical_logic_touched`,
`deployment_or_runtime_safety_touched`, and `resource_exhaustion_or_capacity_risk`.
Material public-contract, dependency/protocol, and generated/shared-artifact risks use their
corresponding `*_material*` keys from `policy_defs.py`.

Materiality matters. Cosmetic public labels, routine lockfile churn, or benign generated snapshots
are not review triggers merely because a file changed. Set the corresponding `*_material*` flag
only when semantics, compatibility, release behavior, or meaningful risk changes.

Run:

```bash
python .codex/slt-tools/routing_policy.py --input <classification.json>
```

The script deterministically maps supplied flags/execution class to named agents. Terra must not
override the result merely to save tokens.

Product choices, business approvals, and missing user preferences belong to the user, not Sol.

## 3. Decision gate and review risk are deliberately separate

`decision_gate` asks: **Is there an unresolved material decision that blocks safe implementation?**

`review_risk` asks: **Did the integrated implementation materially touch a domain that deserves
Sol final review even when design was already approved?**

A frozen auth implementation can therefore skip Sol Architect but still require Sol Reviewer.
This separation exists to reduce duplicate Sol calls.

## 4. Sol context packet

When crossing either Sol gate, use `references/context-packet.md` v0.4.0.

Start with:
- original requirement and exact base revision;
- evidence-backed observed facts;
- invariants and unresolved questions;
- exact decision/review flags;
- relevant paths/symbols and why they matter;
- active contract ids/hashes and snapshot exclusions;
- relevant patch;
- writer-lock/write-set status;
- exact verification evidence.

Sol should directly read targeted surrounding symbols/contracts/tests when needed. Prefer reuse of
the earlier Sol thread when the client safely supports it. Otherwise send a complete versioned
packet. Do not duplicate full patch plus full files by default.

## 5. Machine-verifiable writer contract

Every delegated writer requires a JSON contract based on `references/task-contract.md`.

The contract includes:
- exact `base_revision` equal to current HEAD;
- immutable `contract_hash`;
- read/allowed/forbidden scopes;
- declared shared/generated files;
- explicit `snapshot_exclude` patterns;
- verification/integration commands;
- decision and review-risk classifications;
- escalation conditions.

`snapshot_exclude` exists only for explicitly accepted performance exclusions such as huge
throwaway dependency/cache trees. Excluded paths are not protected. Never silently exclude
secrets, material local configuration, migrations, or release artifacts.

## 6. Single-writer lock and protected baseline

For delegated writes in a shared worktree, acquire the lock first:

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id <TASK-ID>
```

The lock lives in the current Git worktree's private gitdir. A second writer in the same worktree
fails to acquire it. Separate Git worktrees have separate locks and may be used for intentional
parallel writers.

Then run:

```bash
python .codex/slt-tools/contract_guard.py hash-contract --contract <contract.json> --write
python .codex/slt-tools/contract_guard.py validate-task-contract --contract <contract.json>
python .codex/slt-tools/contract_guard.py create-task-baseline --contract <contract.json>
```

Baseline creation requires the matching writer lock and rejects stale `base_revision` values.
The baseline is stored outside the normal workspace under the current worktree's Git metadata,
which reduces accidental worker tampering. The worker does not need the baseline path.

## 7. Implementation routing

Use the routing-script result.

### `luna_fast` — Luna High
Mechanical bounded edits with frozen behavior and objective verification.

### `luna_worker` — Luna Max
Bounded implementation needing local logic reasoning but no material design decision.

### `terra_worker` — Terra High
Complex/multi-file but already-decided implementation, integration-aware repair, or focused
debugging with a defined expected outcome.

If a worker discovers an unresolved decision, contract expansion, or repeated/non-deterministic
failure, stop and reclassify rather than guessing.

## 8. Write-set verification

After every delegated writer and before accepting its result:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set --contract <contract.json>
```

The guard compares against the protected baseline and includes:
- tracked files;
- non-ignored untracked files;
- ignored untracked files, including pre-existing ignored files whose contents changed;
- deletions, binary content changes, renames as path changes, and symlink changes where supported.

It rejects:
- stale/changed HEAD;
- contract/hash mismatch against the baseline;
- forbidden paths;
- undeclared paths.

`allowed_files` remains a post-write contract guard, not a pre-write sandbox ACL. A malicious or
non-cooperative process with broader filesystem permissions is outside this tool's guarantee.

After the parent accepts the guarded write set, release the lock:

```bash
python .codex/slt-tools/writer_lock.py release --task-id <TASK-ID>
```

Do not silently bless an undeclared write by editing the old contract after the fact. Investigate,
revert/repair as appropriate, then issue an explicitly revised contract and new baseline.

## 9. Parallelism

The project config permits at most two child threads, but this is not a writer semaphore.
`writer_lock.py` is the same-worktree writer semaphore.

Rules:
- one active writer per shared worktree;
- for parallel writers, use separate Git worktrees and separate task contracts/baselines;
- serialize shared external resources: databases, dev servers, migrations, lockfiles, generated
  release artifacts, broad formatters, and mutable full builds/tests even across worktrees when
  those resources are shared;
- read-only reconnaissance/triage may use the second child when useful.

## 10. Integration and final review routing

Terra integrates the result, checks complete diff versus contracts, runs scoped then integration
verification, and records any new risks.

Do **not** mutate a hashed task contract merely to update final review risk. Create a final routing
classification from the actual integrated diff and verification evidence, then run
`routing_policy.py` again.

If `reviewer_required` is true, invoke `sol_reviewer`. If false and verification is complete, skip
Sol review. Task size alone is not a review trigger.

For blocker/important review findings, create a bounded repair. Reinvoke Sol only when the repair
changes material assumptions or the final review-risk classification still requires it.

## 11. Completion handoff

Report:
- semantic classification and routing-script result;
- Sol calls made and why;
- named worker allocation;
- contract ids/hashes and snapshot exclusions;
- writer-lock and protected-baseline status;
- deterministic write-set results;
- exact verification commands/results;
- final material review-risk classification and review result;
- unresolved risks or environment limitations.

A prose claim such as `looks good` is not verification evidence.
