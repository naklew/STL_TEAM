---
name: sol-luna-team
description: "SLT Hybrid v0.3.0: Terra High parent orchestration with versioned task contracts, deterministic post-classification routing/write-set guards, Luna High/Max bounded workers, and Sol High only for unresolved decisions or actual review risk."
---

# SLT Hybrid v0.3.0

Use this skill for authorized implementation, debugging, refactoring, and test work when Sol-level
judgment is valuable but Sol should not spend tokens on routine exploration and coding.

## Objective and honesty boundary

Optimize for **Sol tokens + rework**, not minimum total tokens.

This package has two different kinds of control:

1. **Semantic classification remains model/user judgment.** Terra evaluates evidence and marks
   `decision_gate`, `review_risk`, and execution class.
2. **After those values are supplied, routing, contract hashing/version checks, baseline capture,
   and write-set verification are deterministic scripts.**

Do not describe the semantic classifier as code-enforced or fully deterministic.

## Required parent and bundle preflight

Recommended parent session:
- model: `gpt-5.6-terra`
- reasoning: `high`

The skill cannot switch the parent model. If the current parent is not known to be Terra High,
state that limitation before non-trivial delegation.

Before spawning named workers, verify the project contains:
- `.codex/slt-team.json`
- `.codex/agents/luna-fast.toml`
- `.codex/agents/luna-worker.toml`
- `.codex/agents/terra-worker.toml`
- `.codex/agents/sol-architect.toml`
- `.codex/agents/sol-reviewer.toml`
- `.codex/slt-tools/contract_guard.py`
- `.codex/slt-tools/routing_policy.py`

The manifest must report `policy_version = 0.3.0` and `agent_bundle_version = 0.3.0`.
If the bundle is missing or stale, do not silently delegate with guessed models. Ask the user to
install/update the bundle with `scripts/slt_setup.py` from this repository, or continue only in an
explicit single-parent safe mode.

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
| Final high-risk review | `sol_reviewer` | Sol High |

## 1. Trivial fast path

Do not create a team for an obviously trivial change. The Terra parent may edit directly when all
of the following hold:
- at most one or two narrowly scoped files are expected;
- acceptance criteria are explicit;
- no unresolved decision-gate flag is true;
- no review-risk domain is expected to be touched;
- no new dependency, migration, generated/shared artifact, or public contract is involved;
- verification is obvious and local.

After the direct edit, inspect the diff and run the relevant verification. If the task stops being
trivial, enter the normal workflow instead of stretching the fast path.

## 2. Reconnaissance and semantic classification

Terra inspects repository instructions, current diff, relevant modules/contracts/tests,
shared/generated artifacts, and verification commands. Preserve pre-existing user changes.
Record observed facts with file/symbol or command evidence.

For non-trivial work create a routing classification JSON under `.codex/slt-state/` with:

```json
{
  "policy_version": "0.3.0",
  "decision_gate": {
    "unresolved_architecture": false,
    "ambiguous_requirement": false,
    "competing_root_causes": false,
    "contract_expansion_required": false,
    "unresolved_security_policy": false,
    "external_contract_unknown": false,
    "migration_strategy_unresolved": false,
    "concurrency_semantics_unresolved": false,
    "irreversible_operation_unresolved": false,
    "repeated_failure": false
  },
  "review_risk": {
    "public_contract_touched": false,
    "schema_or_migration_touched": false,
    "auth_or_permission_touched": false,
    "concurrency_or_transaction_touched": false,
    "irreversible_operation_touched": false,
    "new_dependency_or_protocol_touched": false,
    "weak_test_oracle": false,
    "generated_or_shared_artifact_touched": false,
    "repeated_failure_or_flaky": false
  },
  "execution": {
    "task_class": "bounded",
    "bounded_reasoning": "mechanical"
  }
}
```

Run:

```bash
python .codex/slt-tools/routing_policy.py --input <classification.json>
```

The script deterministically maps the supplied flags to named agents. Terra must not override the
script merely to save tokens.

Product choices, business approvals, and missing user preferences belong to the user, not Sol.

## 3. Decision gate and review risk are different

### `decision_gate`

This asks whether **an unresolved material decision blocks safe implementation**.
Any true flag requires `sol_architect` before implementation continues.

Typical reasons:
- architecture or acceptance criteria are unresolved;
- plausible root causes imply materially different fixes;
- security/auth policy itself is unresolved;
- external contract or compatibility expectations are unknown;
- migration, concurrency, transaction, idempotency, locking, ordering, or destructive semantics
  are unresolved;
- implementation needs contract expansion;
- a bounded task repeatedly fails.

### `review_risk`

This asks whether **the actual implementation touches a domain that deserves Sol final review**,
even if its design was already approved.

Examples:
- public API/contract touched;
- schema or migration touched;
- auth/permission behavior touched;
- concurrency/transaction behavior touched;
- irreversible operation touched;
- dependency/protocol changed;
- test oracle is weak;
- shared/generated artifacts changed;
- repeated failure or flaky behavior remains relevant.

A frozen auth implementation can therefore skip Sol Architect but still require Sol Reviewer.
This separation is intentional to avoid duplicate Sol calls.

## 4. Sol context packet

When crossing either Sol gate, use `references/context-packet.md` version 0.3.0.

Do not give Sol only a prose summary and do not dump the repository. Start with:
- original requirement and base revision;
- evidence-backed observed facts;
- invariants and unresolved questions;
- exact decision/review flags;
- relevant paths/symbols and why they matter;
- active contract ids and hashes;
- relevant patch;
- exact verification evidence.

Sol should directly read targeted surrounding symbols/contracts/tests when needed.
Prefer the same Sol thread for final review when the client safely supports reuse. Otherwise send
a complete versioned packet. Do not duplicate full patch plus full files by default.

## 5. Machine-verifiable task contracts

Every delegated writer requires a JSON contract based on `references/task-contract.md`.
The contract is immutable after hashing/baseline creation. If the boundary or decision changes,
create a revised contract and a new baseline; do not silently edit the old one.

Required sequence before spawn:

```bash
python .codex/slt-tools/contract_guard.py hash-contract --contract <contract.json> --write
python .codex/slt-tools/contract_guard.py validate-task-contract --contract <contract.json>
python .codex/slt-tools/contract_guard.py create-task-baseline --contract <contract.json>
```

A contract includes version fields, base revision, read scope, allowed/forbidden files,
shared/generated artifacts, acceptance criteria, scoped/integration verification, execution class,
decision flags, review-risk prediction, and escalation conditions.

`allowed_files` is not a sandbox ACL. The guard detects violations after execution.

## 6. Implementation routing

Use the routing script result.

### `luna_fast` — Luna High
Use only for mechanical bounded edits with frozen behavior and objective verification.
Examples: explicit mappings, fixtures, narrow repetitive tests, simple configuration/text changes.

### `luna_worker` — Luna Max
Use for bounded implementation that needs local logic reasoning but no material design decision.

### `terra_worker` — Terra High
Use for complex/multi-file but already-decided implementation, integration-aware repair, or focused
debugging with a defined expected outcome.

If a worker discovers an unresolved decision, contract expansion, or repeated/non-deterministic
failure, stop and reclassify rather than guessing.

## 7. Deterministic write-set check

After every delegated writer and before accepting its result, run:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set --contract <contract.json>
```

Exit code 0 means the changed paths fit the contract. A non-zero result is a failed task boundary.
Do not silently bless an undeclared write by editing `allowed_files` after the fact. Investigate,
revert/repair as appropriate, and issue a revised contract only after the broader scope is approved.

The baseline is a path-by-path content snapshot, so pre-existing dirty tracked/untracked files are
preserved rather than assumed clean.

## 8. Parallelism

The bundled project config permits at most two child threads. Within a shared workspace:
- default to **one active writer**;
- a second writer is allowed only for genuinely independent files and generated/shared artifacts;
- prefer separate worktrees for write-heavy concurrency;
- serialize lockfiles, migrations, generated code, snapshots, broad formatters, mutable full
  builds/tests, shared dev servers, and shared databases;
- read-only reconnaissance/triage may use the available second child when useful.

The concurrency limit is not a writer semaphore; the parent must still enforce single-writer policy.

## 9. Integration and final review routing

Terra integrates the result, checks complete diff versus baseline/contracts, runs scoped then
integration verification, and records any new risks.

Do **not** mutate hashed task contracts merely to update final review risk. Create a final routing
classification from the actual integrated diff and verification evidence, then run
`routing_policy.py` again.

If `reviewer_required` is true, invoke `sol_reviewer`. If false and verification is complete, skip
Sol review. Task size alone is not a review trigger.

For blocker/important review findings, create a bounded repair. Reinvoke Sol only when the repair
changes material assumptions or the final review-risk classification still requires it.

## 10. Completion handoff

Report:
- semantic classification and routing-script result;
- Sol calls made and why;
- named worker allocation;
- contract ids/hashes;
- deterministic write-set results;
- exact verification commands/results;
- final review-risk classification and review result;
- unresolved risks or environment limitations.

A prose claim such as `looks good` is not verification evidence.
