# Task contract

Create one contract per delegated work item. The contract should be executable
without asking the worker to rediscover architecture or infer hidden requirements.

```yaml
id: AUTH-003
goal: Implement the login endpoint without changing the existing API contract.

context:
  - Architecture decision: reuse the existing JWT helper.
  - Password hashing exists in src/auth/passwords.py.
  - Repository uses pytest.

allowed_files:
  - src/auth/login.py
  - tests/auth/test_login.py

forbidden_files:
  - src/db/schema.py
  - src/models/user.py
  - public API response definitions

acceptance_criteria:
  - Correct credentials return 200 and a JWT.
  - Incorrect credentials return 401.
  - Unknown users return 401 without leaking account existence.
  - Existing relevant tests remain green.

verification:
  - pytest tests/auth/test_login.py

dependencies: []

escalation_conditions:
  - response contract must change
  - user model/schema must change
  - existing helper behavior contradicts the contract
```

## Routing rules

Send to Luna when the contract is narrow, objective, file-bounded, and independently verifiable.

Send to Terra when implementation is multi-file or integration-heavy but the architecture
and expected behavior are already decided.

Return to Sol when execution discovers a material decision about architecture, schema,
public interfaces, security behavior, or ambiguous requirements.

`allowed_files` is a write boundary, not a suggestion.
