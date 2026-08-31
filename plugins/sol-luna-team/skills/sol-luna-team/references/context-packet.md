# Sol context packet v0.3.0

Use this packet only when crossing a Sol decision gate or final review gate. The goal is to avoid
both whole-repository dumps and lossy Terra-only summaries.

```yaml
context_packet_version: "0.3.0"
policy_version: "0.3.0"
agent_bundle_version: "0.3.0"
base_revision: <git sha or working baseline>
original_requirement: <verbatim or minimally normalized user request>

observed_facts:
  - fact: <directly observed behavior/code fact>
    evidence: <file:symbol, exact command result, test, or patch hunk>

invariants:
  - <behavior or contract that must remain true>
unknowns:
  - <only questions that materially affect the current gate>
decisions_already_made:
  - <decision and source>

relevant_files:
  - path: src/example.py
    symbols: [ExampleClass.method]
    reason: Owns the behavior under discussion.

alternative_designs:
  - option: <candidate>
    evidence_for: <short evidence>
    evidence_against: <short evidence>

rejected_alternatives:
  - option: <candidate>
    reason: <why rejected>

decision_gate:
  unresolved_architecture: false
  ambiguous_requirement: false
  competing_root_causes: false
  contract_expansion_required: false
  unresolved_security_policy: false
  external_contract_unknown: false
  migration_strategy_unresolved: false
  concurrency_semantics_unresolved: false
  irreversible_operation_unresolved: false
  repeated_failure: false

review_risk:
  public_contract_touched: false
  schema_or_migration_touched: false
  auth_or_permission_touched: false
  concurrency_or_transaction_touched: false
  irreversible_operation_touched: false
  new_dependency_or_protocol_touched: false
  weak_test_oracle: false
  generated_or_shared_artifact_touched: false
  repeated_failure_or_flaky: false

active_contracts:
  - id: TASK-001
    contract_hash: sha256:...

patch:
  source: git diff or exact patch range
  note: Prefer patch plus targeted surrounding symbols over duplicating full files.

verification:
  - command: <exact command>
    result: passed | failed | not_run
    evidence: <short output or failure reference>
```

## Rules

- Preserve the original requirement; do not silently rewrite product intent.
- Every important observed fact should point to evidence.
- For an architect call, send the unresolved decision flags and only the evidence needed to resolve them.
- For a reviewer call, send the final patch, actual review-risk flags, contracts by id/hash, and verification evidence.
- Do not send full patch plus full source files by default. Start with the patch and let Sol read targeted surrounding symbols directly.
- If the same Sol thread can be safely reused, prefer reuse; otherwise send a complete versioned packet.
- If a necessary fact is missing, Sol should request a targeted read rather than accept Terra's framing.
