---
name: sol-luna-team
description: "Cost-aware Codex development team. Terra leads routine exploration, implementation and integration; Sol is invoked only for architecture/decision gates and final review; Luna performs bounded implementation."
---

# Sol–Luna–Terra cost-aware coding team

Use this skill for authorized software implementation, bug fixes, refactors, and test work
where Sol-level judgment is valuable but spending Sol tokens on the entire implementation is not.

## Objective

Preserve high-quality architectural and review decisions while moving routine token-heavy work
to Terra and Luna.

Recommended parent session:
- `gpt-5.6-terra`
- reasoning `high`

The skill cannot change the parent session model. For best cost/quality behavior, start the
parent Codex session on Terra High.

## Roles

| Work | Agent | Model / effort |
| --- | --- | --- |
| Parent orchestration, repository exploration, integration, verification | `terra_orchestrator` | Terra High |
| Architecture, ambiguous requirements, material design decisions | `sol_architect` | Sol High |
| Narrow independently verifiable implementation | `luna_worker` | Luna Max |
| Multi-file but already-decided implementation / integration repair | `terra_worker` | Terra High |
| Final correctness/security/contract review | `sol_reviewer` | Sol High |

Never escalate to Sol Max automatically. Max is a manual exception for unresolved,
high-impact architecture, debugging, or security decisions.

## Decision gate

Before invoking Sol, ask whether the task requires a material judgment.

Use Sol only for:
- ambiguous requirements
- architecture choices
- public API/interface/schema/data-model changes
- security-sensitive behavior
- conflicting constraints
- hard debugging where materially different hypotheses imply different fixes

Do not use Sol merely for:
- repository search
- locating files
- routine implementation
- running tests/build/lint/type-check
- mechanical refactors
- known-pattern multi-file edits
- straightforward test repair

## Workflow

### 1. Terra reconnaissance

Inspect:
- current repository instructions
- current diff and pre-existing user edits
- relevant modules
- tests/build/lint/type-check commands
- conventions and dependencies

Produce a concise evidence packet. Do not send unrelated repository context to Sol.

### 2. Sol architecture gate, only when needed

Invoke `sol_architect` with:
- user requirement
- concise Terra findings
- relevant files/symbols
- material unknowns
- constraints

Sol returns decisions and bounded task contracts. Sol does not edit code.

If no material decision exists, Terra creates the contracts directly.

### 3. Implementation routing

Use Luna only when:
- goal and acceptance criteria are unambiguous
- work can be independently verified
- allowed files are explicit
- public interfaces/schema/architecture are frozen
- write ownership does not overlap another active worker

Use Terra worker when:
- implementation spans modules
- integration is required
- repository exploration must continue
- a Luna failure can be repaired without a new design decision

If execution discovers a new material decision, stop that item and return to `sol_architect`.

### 4. Parallelism

Start with one worker.

Use two workers when tasks have clearly independent file ownership.
Use three only when independence is obvious and time savings justify the extra token use.

Never run concurrent workers with overlapping write ownership.

### 5. Integration

Terra lead:
1. inspects the complete diff
2. checks every changed file against a contract
3. runs all relevant tests
4. runs lint/type-check/build as applicable
5. repairs integration-only problems that do not require new design decisions

### 6. Sol final review

For medium or large changes, invoke `sol_reviewer` once after integrated verification.

Provide:
- original requirement
- architecture decisions
- task contracts
- complete relevant diff
- verification evidence

Do not send unchanged files unless needed to understand a contract.

If review returns blocker or important findings, create a bounded follow-up for Luna or Terra.
Invoke Sol again only if the repair itself requires a new material decision.

For trivial bounded changes, Sol review may be skipped unless contract/security risk exists.

## Token discipline

- Terra performs repository reconnaissance before Sol.
- Sol receives compressed evidence, not a broad repository dump.
- Sol does not implement routine code.
- Sol does not rerun routine verification.
- Sol reviews relevant diffs, not the whole codebase.
- Avoid repeated Sol reviews after non-material fixes.
- Do not use parallel workers solely because concurrency is available.

## Worker result

```yaml
status: success | blocked | needs_escalation | needs_sol_decision
task_id: TASK-ID
summary: one sentence
files_changed:
  - path
verification:
  - command: command
    result: passed | failed | not_run
    notes: concise evidence
risks:
  - none
escalation_reason: null
```

A prose claim such as "looks good" is not verification evidence.

## Completion handoff

Report:
- Sol decision calls made and why
- Luna/Terra task allocation
- changed files
- exact verification commands and results
- review findings and repairs
- remaining risks
