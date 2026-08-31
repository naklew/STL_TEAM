---
name: sol-luna-team
description: "Hybrid cost-aware Codex team. Terra High leads the parent session, Luna Max handles narrow bounded implementation, Terra High handles already-decided complex work, and Sol High is reserved for objective risk gates and final high-risk review."
---

# SLT Hybrid cost-aware coding team

Use this skill for authorized software implementation, bug fixes, refactors, and test work when Sol-level judgment is valuable but spending Sol tokens on the entire workflow is not.

## Operating objective

Minimize Sol usage without letting lower-cost models make material design decisions accidentally.

Recommended parent session:
- model: `gpt-5.6-terra`
- reasoning: `high`

The skill cannot change the parent model. Start a new parent Codex session on Terra High for the intended behavior.

## Roles

| Work | Agent | Model / effort |
| --- | --- | --- |
| Parent orchestration, reconnaissance, integration, verification | parent session | Terra High |
| Architecture, ambiguous requirements, public contracts, high-risk decisions | `sol_architect` | Sol High |
| Narrow independently verifiable implementation | `luna_worker` | Luna Max |
| Multi-file but already-decided implementation and focused repair | `terra_worker` | Terra High |
| High-risk final correctness/security/contract review | `sol_reviewer` | Sol High |

Do not use a child orchestrator. The parent Terra session follows this skill directly.
Never invoke Sol Max automatically. Recommend Max only after Sol High cannot resolve a high-impact architecture, security, concurrency, or root-cause decision, and obtain user approval before escalation.

## 1. Terra reconnaissance

Before delegation:

1. inspect repository instructions and current working-tree diff;
2. identify the base revision or working baseline;
3. locate relevant modules, public contracts, tests, generated/shared artifacts, and verification commands;
4. preserve pre-existing user changes;
5. record directly observed facts with file/symbol or command evidence.

Read-only reconnaissance may be parallelized to 2-3 workers when useful. Shared-workspace writers should default to one active writer.

## 2. Deterministic risk classifier

Before implementation, populate these flags:

```yaml
risk_flags:
  public_contract_change: false
  schema_or_migration: false
  auth_or_permission: false
  concurrency_or_transaction: false
  irreversible_operation: false
  new_dependency_or_protocol: false
  ambiguous_acceptance_criteria: false
  multiple_plausible_root_causes: false
  contract_expansion_required: false
  repeated_failure: false
  weak_test_oracle_or_test_bypass_risk: false
  generated_or_shared_artifact_change: false
```

### Mandatory Sol decision gate

Invoke `sol_architect` before implementation, or return to it immediately if discovered later, when a material flag is true:

- public contract/API/interface behavior changes;
- schema, migration, persistence model, or backward compatibility changes;
- authentication, authorization, approval, or trust-boundary behavior changes;
- concurrency, transactionality, idempotency, locking, race, ordering, or distributed consistency decisions are involved;
- an operation is materially irreversible or destructive;
- a new dependency, protocol, framework, or external integration changes system design;
- acceptance criteria are materially ambiguous;
- multiple plausible root causes imply materially different fixes;
- implementation requires expanding the approved contract or file boundary;
- a bounded task has failed twice, is flaky/non-deterministic, or cannot be verified confidently;
- tests pass only because the oracle is weak, behavior is bypassed, or tests appear weakened;
- generated/shared artifacts have cross-task, migration, release, or dependency impact.

Do not send product choices, business approval questions, or missing user preferences to Sol. Ask the user instead.

If all material flags are false and expected behavior is already frozen, Terra may create the task contract directly.

## 3. Sol context packet

When crossing a Sol gate, use `references/context-packet.md`.

Do not give Sol only a prose summary and do not dump the entire repository. Provide:
- original requirement;
- base revision;
- observed facts with evidence;
- invariants and unknowns;
- risk flags;
- exact relevant files/symbols and why they matter;
- alternatives considered;
- current task contracts;
- relevant diff/patch;
- verification evidence.

Sol should directly read the material contract/interface/test/change files when needed. If a relevant fact is missing, Sol may request a targeted read instead of accepting Terra's framing.

If the same Sol thread can safely be reused for final review, reuse it to preserve decision continuity. Thread reuse is an optimization, not a correctness requirement; otherwise send a complete structured context packet to a new Sol reviewer.

## 4. Task contracts

Every delegated writer must receive an explicit contract based on `references/task-contract.md`.

A contract includes:
- `base_revision` and `contract_hash`;
- `read_scope`;
- `allowed_files` and `forbidden_files`;
- `shared_or_generated_files`;
- acceptance criteria;
- scoped verification and integration verification;
- dependencies;
- risk flags and escalation conditions.

`allowed_files` is a prompt-level contract, not a sandbox-enforced ACL. Record the baseline diff before dispatch and compare changed files after completion. Any undeclared changed file is a contract violation until explained and approved.

## 5. Implementation routing

### Luna Max

Use `luna_worker` only when ALL are true:
- design and expected behavior are frozen;
- task is narrow, objective, and independently verifiable;
- file ownership is explicit;
- no mandatory Sol risk flag is unresolved;
- no other active writer owns or may generate the same artifacts.

### Terra High

Use `terra_worker` when:
- implementation spans multiple files but design is already decided;
- integration or repository-aware repair is required;
- a Luna failure can be repaired without a new material decision;
- focused debugging has one evidence-backed hypothesis and a defined expected outcome.

If a worker discovers a mandatory risk flag, contract expansion, or a second failure, stop implementation and return to Sol rather than guessing.

## 6. Parallelism and write safety

Default to one shared-workspace writer.

Allow two writers only when their owned files and generated/shared artifacts are genuinely independent. Prefer separate worktrees if concurrent write-heavy work is necessary.

Serialize:
- lockfile updates;
- migrations;
- generated code;
- snapshots;
- formatters that may touch broad paths;
- full builds/tests that mutate shared state;
- shared development servers or databases.

Read-only explorers/tests/triage may run in parallel when they do not mutate shared state.

## 7. Integration on Terra

After writers finish:

1. inspect the complete diff against the baseline;
2. verify changed files against each task contract;
3. reject or explain undeclared file changes;
4. run scoped tests, then integration-relevant tests;
5. run lint/type-check/build as applicable;
6. distinguish code failures from environment-only limitations;
7. set `repeated_failure` or `weak_test_oracle_or_test_bypass_risk` when evidence warrants it.

Terra may repair integration-only issues only if no new mandatory Sol flag becomes true.

## 8. Risk-based Sol final review

Sol review is mandatory when:
- Sol designed or approved a material decision earlier;
- any high-risk flag was true;
- security/auth/schema/concurrency/public-contract behavior changed;
- verification evidence is incomplete or test quality is questionable;
- the final diff materially exceeds the original bounded plan.

Sol review is conditional for routine medium changes and may be skipped for trivial, objectively verified, low-risk changes.

Provide the original requirement, Sol decisions, contracts, relevant diff, risk flags, and verification evidence. Do not send unchanged unrelated files.

If review returns blocker/important findings, create a bounded repair for Luna or Terra. Reinvoke Sol only when the repair changes a material decision, invalidates the prior review assumptions, or itself crosses a mandatory risk flag.

## 9. Token discipline

- Terra performs reconnaissance and routine verification.
- Luna handles only cheap, bounded execution.
- Sol handles decision gates and high-risk review, not routine coding.
- Do not repeat repository exploration in Sol when Terra has already indexed the evidence.
- Do not hide relevant raw evidence behind summaries.
- Do not parallelize merely because concurrency exists.
- Optimize for `Sol tokens + rework`, not minimum total tokens.

## Worker result

```yaml
status: success | blocked | needs_escalation | needs_sol_decision
task_id: TASK-ID
contract_hash: <hash>
summary: one sentence
files_changed:
  - path
verification:
  - command: command
    result: passed | failed | not_run
    notes: concise evidence
risk_flags_changed:
  - none
risks:
  - none
escalation_reason: null
```

A prose claim such as `looks good` is not verification evidence.

## Completion handoff

Report:
- Sol decision/review calls made and why;
- task allocation to Luna/Terra;
- changed files and contract-boundary checks;
- exact verification commands and results;
- review findings and repairs;
- unresolved risks and environment limitations.
