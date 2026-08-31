# Machine-verifiable task contract v0.4.0

SLT uses JSON contracts for delegated writers. Runtime contracts, locks, and default baseline files live under the target worktree's `.codex/slt-state/`, which is writable under normal Codex `workspace-write`.

Baseline integrity is **not** based on hiding that file from the worker. `create-task-baseline` returns a SHA-256 seal that the parent retains and supplies only during final verification. If the baseline bytes are changed, verification fails before the baseline is trusted.

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

This example intentionally separates review risk from an unresolved decision: auth behavior is touched, so Sol Reviewer is required, while the already-approved auth policy does not require Sol Architect.

## `snapshot_exclude`

The guard snapshots tracked files, non-ignored untracked files, and ignored untracked files. Huge disposable trees such as `node_modules/**` or `.venv/**` may be explicitly listed in `snapshot_exclude` for performance.

Every exclusion becomes part of the immutable contract hash. Excluded paths are **not protected by write-set verification**. Do not exclude secrets, material runtime configuration, migrations, generated release artifacts, or other paths whose mutation matters.

## Required command sequence

Acquire the worktree-local writer lock:

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id AUTH-003
```

Then hash, validate, and create the baseline:

```bash
python .codex/slt-tools/contract_guard.py hash-contract \
  --contract .codex/slt-state/AUTH-003.contract.json --write

python .codex/slt-tools/contract_guard.py validate-task-contract \
  --contract .codex/slt-state/AUTH-003.contract.json

python .codex/slt-tools/contract_guard.py create-task-baseline \
  --contract .codex/slt-state/AUTH-003.contract.json --json
```

The final command returns data like:

```json
{
  "baseline": "<worktree>/.codex/slt-state/baselines/AUTH-003.baseline.json",
  "baseline_sha256": "sha256:<64 hex chars>"
}
```

The **parent retains `baseline_sha256` and does not give the seal to the writer**. The baseline file itself is workspace-local so that ordinary Codex `workspace-write` can create it. It is tamper-evident rather than filesystem-inaccessible.

`create-task-baseline` refuses to run if the matching writer lock is absent, `base_revision` differs from current HEAD, or the contract/hash/version is invalid.

After the writer returns, the parent runs:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract .codex/slt-state/AUTH-003.contract.json \
  --baseline-sha sha256:<parent-held seal>
```

Verification rejects:
- baseline-byte changes relative to the parent-held seal;
- contract/hash tampering relative to the sealed baseline;
- HEAD changes after baseline creation;
- forbidden or undeclared changed paths;
- tracked, normal-untracked, and ignored-file mutations outside the declared boundary;
- case-only rename targets such as `foo.txt -> FOO.txt`, including on Windows case-insensitive worktrees.

Release the lock only after the parent accepts verification:

```bash
python .codex/slt-tools/writer_lock.py release --task-id AUTH-003
```

A non-zero guard result is a failed contract. Do not silently expand `allowed_files`; investigate/revert as appropriate and create an explicitly revised contract and fresh baseline.

## Safety boundary

This is a machine-verifiable **cooperative post-write guard**, not a pre-write filesystem ACL and not a cryptographic security boundary against a malicious process that can read or alter the parent context. The parent-held seal protects against baseline mutation by an ordinary delegated writer that is not given the seal.

## Decision gate versus review risk

`decision_gate` means an unresolved material decision blocks safe implementation.

`review_risk` means the integrated implementation materially touches a domain deserving Sol review even when design was already approved.

Materiality is intentional. Cosmetic public labels, routine lockfile churn, or benign generated snapshots should not set the corresponding `*_material*` flags unless semantics, compatibility, release behavior, or meaningful risk changes.
