# Machine-verifiable task contract

SLT 0.3.0 uses JSON for the execution contract because `contract_guard.py` hashes and validates
it deterministically. YAML may be used for human notes, but the worker boundary is the JSON file.

Store runtime contracts under `.codex/slt-state/` so the setup tool can keep them out of normal
Git diffs.

## Contract shape

```json
{
  "id": "AUTH-003",
  "policy_version": "0.3.0",
  "agent_bundle_version": "0.3.0",
  "base_revision": "<git sha or working-tree baseline>",
  "contract_hash": "<filled by contract_guard.py>",
  "goal": "Implement the login endpoint without changing the existing API contract.",
  "context": [
    "Architecture decision: reuse the existing JWT helper.",
    "Password hashing exists in src/auth/passwords.py."
  ],
  "read_scope": [
    "src/auth/passwords.py",
    "src/auth/login.py",
    "tests/auth/test_login.py"
  ],
  "allowed_files": [
    "src/auth/login.py",
    "tests/auth/test_login.py"
  ],
  "forbidden_files": [
    "src/db/schema.py",
    "src/models/user.py"
  ],
  "shared_or_generated_files": [],
  "acceptance_criteria": [
    "Correct credentials return 200 and a JWT.",
    "Incorrect credentials and unknown users return 401 without account enumeration."
  ],
  "verification": [
    "pytest tests/auth/test_login.py"
  ],
  "integration_verification": [
    "pytest tests/auth"
  ],
  "dependencies": [],
  "execution": {
    "task_class": "bounded",
    "bounded_reasoning": "logic"
  },
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
    "auth_or_permission_touched": true,
    "concurrency_or_transaction_touched": false,
    "irreversible_operation_touched": false,
    "new_dependency_or_protocol_touched": false,
    "weak_test_oracle": false,
    "generated_or_shared_artifact_touched": false,
    "repeated_failure_or_flaky": false
  },
  "escalation_conditions": [
    "response contract must change",
    "user model/schema must change",
    "existing helper behavior contradicts the contract"
  ]
}
```

This example intentionally demonstrates the v0.3 split: auth code is being touched, so final Sol
review is required, but the security policy is already resolved, so Sol Architect is not required.

## Required command sequence

After writing the contract:

```bash
python .codex/slt-tools/contract_guard.py hash-contract \
  --contract .codex/slt-state/AUTH-003.contract.json --write

python .codex/slt-tools/contract_guard.py validate-task-contract \
  --contract .codex/slt-state/AUTH-003.contract.json

python .codex/slt-tools/contract_guard.py create-task-baseline \
  --contract .codex/slt-state/AUTH-003.contract.json
```

After the writer returns, before accepting its result:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract .codex/slt-state/AUTH-003.contract.json
```

A non-zero result is a failed contract until the parent investigates it. Do not silently expand
`allowed_files` after the worker has written outside the boundary; create a revised contract,
rehash it, and create a new baseline after the change is explicitly approved.

## Decision gate versus review risk

`decision_gate` answers: **Is there an unresolved material decision that must be resolved before
implementation continues?**

`review_risk` answers: **Did the final implementation touch a domain that requires Sol review even
when its design was already approved?**

This separation avoids paying for Sol Architect merely because an already-frozen auth, schema,
public-contract, or concurrency implementation is high risk to review.
