---
name: sol-luna-team
description: "SLT Hybrid v0.4.0: Terra High parent orchestration with named agents, deterministic post-classification routing, Codex-writable sealed baselines, ignored-file/case-aware write guards, and same-worktree writer locking."
---

# SLT Hybrid v0.4.0

Use this skill for authorized implementation, debugging, refactoring, and test work when Sol-level judgment is valuable but Sol should not spend tokens on routine exploration and coding.

## Objective and honesty boundary

Optimize for **Sol tokens + avoidable rework**, not minimum total tokens.

This package separates semantic judgment from machine enforcement:

1. **Semantic classification remains model/user judgment.** Terra evaluates evidence and marks `decision_gate`, `review_risk`, execution class, and explicit snapshot exclusions.
2. **After classification, routing, version checks, contract hashing, base-revision checks, writer locking, baseline sealing, and write-set verification are deterministic scripts.**

Do not describe the semantic classifier as code-enforced or fully deterministic. The package is a policy-guided orchestrator with deterministic guards around mechanically verifiable parts.

## Required parent and bundle preflight

Recommended parent session:
- model: `gpt-5.6-terra`
- reasoning: `high`

The skill cannot switch the parent model. If the current parent is not known to be Terra High, state that limitation before non-trivial delegation.

Before spawning named workers, run:

```bash
python scripts/slt_setup.py status <target-project>
```

The command must return success. It verifies version alignment, hashes of managed agents/tools, `.codex/config.toml`, and worktree-safe Git exclude configuration.

Required managed files include:
- `.codex/agents/luna-fast.toml`
- `.codex/agents/luna-worker.toml`
- `.codex/agents/terra-worker.toml`
- `.codex/agents/sol-architect.toml`
- `.codex/agents/sol-reviewer.toml`
- `.codex/slt-tools/policy_defs.py`
- `.codex/slt-tools/routing_policy.py`
- `.codex/slt-tools/contract_guard.py`
- `.codex/slt-tools/writer_lock.py`

The manifest must report `policy_version = 0.4.0` and `agent_bundle_version = 0.4.0`. If status fails, do not silently delegate with guessed/stale models. Update the bundle or continue only in explicit single-parent safe mode.

Do not use a child orchestrator. The Terra parent follows this skill directly. Never invoke Sol Max automatically. Sol Max requires an unresolved high-impact decision after Sol High plus explicit user approval.

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

The Terra parent may edit directly when all of the following hold:
- at most one or two narrowly scoped files are expected;
- acceptance criteria are explicit;
- no unresolved decision-gate flag is true;
- no material review-risk domain is expected;
- no new dependency, migration, generated/shared release artifact, security boundary, domain-critical logic, deployment/runtime safety, or public contract is involved;
- verification is obvious and local.

If the task stops being trivial, enter the normal workflow.

## 2. Reconnaissance and semantic classification

Terra inspects repository instructions, current diff, relevant modules/contracts/tests, shared/generated artifacts, ignored-but-material local files, and verification commands. Preserve pre-existing user changes and record observed facts with evidence.

Create routing classification JSON under `.codex/slt-state/`. Exact flag names are defined in `.codex/slt-tools/policy_defs.py` and validated by `routing_policy.py`.

### Decision gate

Set a `decision_gate` flag when a material question is unresolved, including architecture/acceptance criteria, competing root causes, contract expansion, security/trust-boundary semantics, external compatibility, migration strategy, data-integrity/loss semantics, domain-critical behavior, concurrency/transaction semantics, deployment/runtime safety, resource/capacity semantics, irreversible behavior, or repeated failure.

Any true decision flag requires `sol_architect` before implementation.

### Review risk and materiality

Set `review_risk` when the integrated implementation materially touches public compatibility, schema/migration, auth/permission, security/trust boundaries, data integrity/loss, domain-critical algorithms, concurrency/transactions, irreversible operations, material dependencies/protocols, deployment/runtime safety, resource/capacity risk, weak test oracles, material generated/shared artifacts, or repeated/flaky failure.

The exact v0.4 keys include `security_boundary_touched`, `data_integrity_or_loss_risk`, `domain_critical_logic_touched`, `deployment_or_runtime_safety_touched`, and `resource_exhaustion_or_capacity_risk`. Public-contract, dependency/protocol, and generated/shared-artifact risks use `*_material*` keys.

Materiality matters. Cosmetic public labels, routine lockfile churn, or benign generated snapshots are not review triggers merely because a file changed.

Run:

```bash
python .codex/slt-tools/routing_policy.py --input <classification.json>
```

Terra must not override the script merely to save tokens. Product choices and missing user preferences belong to the user, not Sol.

## 3. Decision gate and review risk are separate

`decision_gate`: **Is an unresolved material decision blocking safe implementation?**

`review_risk`: **Did the integrated implementation materially touch a domain deserving Sol review even if design was already approved?**

A frozen auth implementation can skip Sol Architect but still require Sol Reviewer.

## 4. Sol context packet

When crossing either Sol gate, use `references/context-packet.md` v0.4.0. Start with original requirement/base revision, evidence-backed facts, invariants/unknowns, exact flags, relevant paths/symbols, contract ids/hashes, relevant patch, lock/write-set status, and exact verification evidence.

Sol should directly read targeted surrounding symbols/contracts/tests when needed. Prefer reuse of the earlier Sol thread when safely supported. Do not duplicate full patch plus full files by default.

## 5. Machine-verifiable writer contract

Every delegated writer requires JSON based on `references/task-contract.md`, including exact `base_revision`, immutable `contract_hash`, read/allowed/forbidden scopes, shared/generated files, `snapshot_exclude`, verification commands, routing flags, and escalation conditions.

`snapshot_exclude` is only for explicit performance exclusions such as huge disposable dependency/cache trees. Excluded paths are not protected. Never silently exclude secrets, material configuration, migrations, or release artifacts.

## 6. Workspace-safe writer lock and parent-held baseline seal

Acquire the same-worktree writer lock first:

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id <TASK-ID>
```

By default the lock lives under the target worktree's `.codex/slt-state/locks/`, not `.git`, so normal Codex `workspace-write` can create it. Separate Git worktrees have separate state directories and can intentionally run independent writers. `SLT_STATE_HOME` is an optional explicit override, not the default.

Then hash, validate, and create a baseline:

```bash
python .codex/slt-tools/contract_guard.py hash-contract --contract <contract.json> --write
python .codex/slt-tools/contract_guard.py validate-task-contract --contract <contract.json>
python .codex/slt-tools/contract_guard.py create-task-baseline --contract <contract.json> --json
```

`create-task-baseline` returns both:
- `baseline`: baseline file path;
- `baseline_sha256`: SHA-256 seal of the exact baseline bytes.

**The parent must retain `baseline_sha256` and must not provide that seal to the writer.** The default baseline is stored under `.codex/slt-state/baselines/`, which is writable in the normal workspace. It is therefore not protected by filesystem secrecy. Instead, tampering is detected because final verification requires the parent-held seal and rejects any changed baseline bytes.

This is a cooperative execution guard, not a security boundary against a malicious process with access to the parent context.

Baseline creation also requires the matching writer lock and rejects stale `base_revision` values.

## 7. Implementation routing

Use the routing-script result.

### `luna_fast` — Luna High
Mechanical bounded edits with frozen behavior and objective verification.

### `luna_worker` — Luna Max
Bounded implementation needing local logic reasoning but no material design decision.

### `terra_worker` — Terra High
Complex/multi-file but already-decided implementation, integration-aware repair, or focused debugging with a defined expected outcome.

If a worker discovers an unresolved decision, contract expansion, or repeated/non-deterministic failure, stop and reclassify rather than guessing.

## 8. Sealed write-set verification

After every delegated writer and before accepting its result, the **parent** runs:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract <contract.json> \
  --baseline-sha <PARENT_HELD_BASELINE_SHA256>
```

The guard compares against the baseline and includes:
- tracked files;
- non-ignored untracked files;
- ignored untracked files, including pre-existing ignored files whose contents changed;
- deletions and binary changes;
- rename source/target path changes;
- actual filesystem directory-entry casing so Windows case-only renames such as `foo.txt -> FOO.txt` are visible;
- symlink changes where the platform permits symlink creation.

It rejects baseline-seal mismatch, stale/changed HEAD, contract/hash mismatch, forbidden paths, and undeclared paths.

`allowed_files` remains a post-write guard, not a pre-write sandbox ACL. A malicious/non-cooperative process with broader permissions is outside this tool's guarantee.

After acceptance:

```bash
python .codex/slt-tools/writer_lock.py release --task-id <TASK-ID>
```

Never silently expand an old contract after a violation. Reclassify and create a revised contract/baseline.

## 9. Parallelism

The project config permits at most two child threads, but that is not a writer semaphore. `writer_lock.py` is the same-worktree cooperating-writer semaphore.

Rules:
- one active writer per shared worktree;
- parallel writers require separate Git worktrees and contracts/baselines;
- serialize shared external resources such as databases, dev servers, migrations, lockfiles, generated release artifacts, broad formatters, and mutable full builds/tests;
- read-only reconnaissance may use the second child when useful.

## 10. Integration and final review

Terra integrates, checks the complete diff, runs scoped then integration verification, and records new risks. Do not mutate a hashed task contract merely to update final review risk; create a final routing classification from the actual integrated diff and verification evidence and run `routing_policy.py` again.

If `reviewer_required` is true, invoke `sol_reviewer`. If false and verification is complete, skip Sol review. Task size alone is not a review trigger.

For blocker/important review findings, create a bounded repair. Reinvoke Sol only when material assumptions change or final risk still requires review.

## 11. Completion handoff

Report:
- semantic classification and routing result;
- Sol calls and reasons;
- named worker allocation;
- contract ids/hashes and snapshot exclusions;
- writer-lock status and parent-held baseline seal verification;
- deterministic write-set results;
- exact verification commands/results;
- final material review-risk classification/review result;
- unresolved risks or environment limitations.

A prose claim such as `looks good` is not verification evidence.
