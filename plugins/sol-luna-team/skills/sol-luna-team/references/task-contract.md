# Task contract

Create one contract per delegated implementation item. The contract must be executable without rediscovering architecture or inferring hidden requirements.

```yaml
id: AUTH-003
base_revision: <git sha or working-tree baseline>
contract_hash: <stable identifier for this exact contract>

goal: Implement the login endpoint without changing the existing API contract.

context:
  - Architecture decision: reuse the existing JWT helper.
  - Password hashing exists in src/auth/passwords.py.
  - Repository uses pytest.

read_scope:
  - src/auth/passwords.py
  - src/auth/login.py
  - tests/auth/test_login.py

allowed_files:
  - src/auth/login.py
  - tests/auth/test_login.py

forbidden_files:
  - src/db/schema.py
  - src/models/user.py
  - public API response definitions

shared_or_generated_files:
  - <lockfiles, migrations, snapshots, generated code, or none>

acceptance_criteria:
  - Correct credentials return 200 and a JWT.
  - Incorrect credentials return 401.
  - Unknown users return 401 without leaking account existence.
  - Existing relevant tests remain green.

verification:
  - pytest tests/auth/test_login.py

integration_verification:
  - pytest tests/auth

dependencies: []

risk_flags:
  public_contract_change: false
  schema_or_migration: false
  auth_or_permission: true
  concurrency_or_transaction: false
  irreversible_operation: false
  new_dependency_or_protocol: false
  ambiguous_acceptance_criteria: false
  multiple_plausible_root_causes: false
  contract_expansion_required: false
  repeated_failure: false
  weak_test_oracle_or_test_bypass_risk: false
  generated_or_shared_artifact_change: false

escalation_conditions:
  - response contract must change
  - user model/schema must change
  - existing helper behavior contradicts the contract
```

## Mandatory Sol-gate triggers

A task must cross a Sol decision gate before implementation, or return to Sol if discovered during implementation, when any of these are true:

- `public_contract_change`
- `schema_or_migration`
- `auth_or_permission`
- `concurrency_or_transaction`
- `irreversible_operation`
- `new_dependency_or_protocol`
- `ambiguous_acceptance_criteria`
- `multiple_plausible_root_causes`
- `contract_expansion_required`
- `repeated_failure`
- `weak_test_oracle_or_test_bypass_risk`
- `generated_or_shared_artifact_change` when the artifact has cross-task or release impact

A user product/approval choice should be asked of the user, not delegated to Sol.

## Routing

Send to Luna only when the design is frozen, the task is narrow and objective, file ownership is explicit, and scoped verification is independent.

Send to Terra when implementation is multi-file or integration-heavy but all material design decisions are already frozen.

Return to Sol when a mandatory risk flag becomes true or execution reveals a material decision not represented in the contract.

## Write-boundary verification

`allowed_files` is a contractual write boundary, not a sandbox guarantee. Before dispatch, record the baseline diff. After the worker returns, compare changed files against `allowed_files` plus explicitly declared `shared_or_generated_files`.

Any undeclared changed file is a contract violation until explained and approved. Build, formatter, migration, lockfile, generated-code, and full-suite operations should be serialized unless isolated worktrees make concurrent writes safe.
