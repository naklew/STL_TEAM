# Machine-verifiable task contract v0.4.0

SLT 0.4.0 uses JSON for delegated writer contracts. Runtime contract files live under
`.codex/slt-state/`, while the protected baseline is stored outside the worktree in the current
Git worktree's private gitdir.

## Contract shape

```json
{
  "id": "AUTH-003",
  "policy_version": "0.4.0",
  "agent_bundle_version": "0.4.0",
  "base_revision": "<exact current HEAD sha>",
  "contract_hash": "<filled by contract_guard.py>",
  "goal": "Implement the login endpoint without changing the existing API contract.",
  "context": ["Security policy is already approved; reuse the existing JWT helper."],
  "read_scope": ["src/auth/passwords.py", "src/auth/login.py", "tests/auth/test_login.py"],
  "allowed_files": ["src/auth/login.py", "tests/auth/test_login.py"],
  "forbidden_files": ["src/db/schema.py", "src/models/user.py"],
  "shared_or_generated_files": [],
  "snapshot_exclude": [],
  "acceptance_criteria": [
    "Correct credentials return 200 and a JWT.",
    "Incorrect credentials and unknown users return 401 without account enumeration."
  ],
  "verification": ["pytest tests/auth/test_login.py"],
  "integration_verification": ["pytest tests/auth"],
  "dependencies": [],
  "execution": {"task_class": "bounded", "bounded_reasoning": "logic"},
  "decision_gate": {
    "unresolved_architecture": false,
    "ambiguous_requirement": false,
    "competing_root_causes": false,
    "contract_expansion_required": false,
    "unresolved_security_policy": false,
    "security_boundary_unresolved": false,
    "external_contract_unknown": false,
    "migration_strategy_unresolved": false,
    "data_integrity_semantics_unresolved": false,
    "domain_critical_behavior_unresolved": false,
    "concurrency_semantics_unresolved": false,
    "deployment_runtime_safety_unresolved": false,
    "resource_capacity_semantics_unresolved": false,
    "irreversible_operation_unresolved": false,
    "repeated_failure": false
  },
  "review_risk": {
    "public_contract_material_change": false,
    "schema_or_migration_touched": false,
    "auth_or_permission_touched": true,
    "security_boundary_touched": false,
    "data_integrity_or_loss_risk": false,
    "domain_critical_logic_touched": false,
    "concurrency_or_transaction_touched": false,
    "irreversible_operation_touched": false,
    "new_dependency_or_protocol_material": false,
    "deployment_or_runtime_safety_touched": false,
    "resource_exhaustion_or_capacity_risk": false,
    "weak_test_oracle": false,
    "generated_or_shared_artifact_material": false,
    "repeated_failure_or_flaky": false
  },
  "escalation_conditions": [
    "response contract must change",
    "user model/schema must change",
    "existing helper behavior contradicts the contract"
  ]
}
```

This intentionally demonstrates the split: auth behavior is touched, so Sol Reviewer is required,
but the auth/security policy is already resolved, so Sol Architect is not required.

## `snapshot_exclude`

The guard now includes tracked files, non-ignored untracked files, and ignored untracked files.
If a repository has huge disposable trees such as `node_modules/**` or `.venv/**`, they may be
listed in `snapshot_exclude` for performance. Every exclusion is therefore explicit and becomes
part of the immutable contract hash. Excluded paths are **not protected by write-set verification**.
Do not exclude secrets, runtime configuration, generated release artifacts, migrations, or other
files whose mutation matters to the task.

## Required command sequence

Acquire the worktree writer lock before baseline creation:

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id AUTH-003
```

Then hash, validate, and snapshot:

```bash
python .codex/slt-tools/contract_guard.py hash-contract \
  --contract .codex/slt-state/AUTH-003.contract.json --write
python .codex/slt-tools/contract_guard.py validate-task-contract \
  --contract .codex/slt-state/AUTH-003.contract.json
python .codex/slt-tools/contract_guard.py create-task-baseline \
  --contract .codex/slt-state/AUTH-003.contract.json
```

`create-task-baseline` refuses to run if:
- the writer lock is absent or belongs to another task;
- `base_revision` does not equal the current HEAD;
- the contract/hash/version is invalid.

The baseline is stored under Git metadata (`git rev-parse --git-path slt-baselines/...`), not in the
normal workspace. The worker does not need its path.

After the writer returns:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract .codex/slt-state/AUTH-003.contract.json
```

Verification rejects:
- contract/hash tampering relative to the protected baseline;
- HEAD changes after baseline creation;
- forbidden or undeclared changed paths;
- tracked, non-ignored untracked, and ignored-file mutations outside the declared boundary.

Release the lock only after the parent has accepted the write-set result:

```bash
python .codex/slt-tools/writer_lock.py release --task-id AUTH-003
```

A non-zero guard result is a failed contract. Never silently expand `allowed_files` after a
violation. Investigate/revert as appropriate, create an explicitly revised contract, acquire the
lock, rehash, and create a fresh baseline.

## Decision gate versus review risk

`decision_gate` means **an unresolved material decision blocks safe implementation**.

`review_risk` means **the integrated implementation materially touches a domain deserving Sol
review even when the design was already approved**.

Materiality is intentional. A cosmetic public label, routine lockfile churn, or benign generated
snapshot should not set `public_contract_material_change`, `new_dependency_or_protocol_material`,
or `generated_or_shared_artifact_material` unless it changes semantics, compatibility, release
behavior, or risk.
