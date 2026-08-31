# Sol context packet v0.4.0

Use this packet only when crossing a Sol decision gate or final review gate. It is an evidence
index, not a whole-repository dump and not a Terra-only prose summary.

```yaml
context_packet_version: "0.4.0"
policy_version: "0.4.0"
agent_bundle_version: "0.4.0"
base_revision: <exact HEAD used by active contracts>
original_requirement: <verbatim or minimally normalized user request>

observed_facts:
  - fact: <directly observed behavior/code fact>
    evidence: <file:symbol, exact command result, test, or patch hunk>

invariants:
  - <behavior/contract that must remain true>
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
  security_boundary_unresolved: false
  external_contract_unknown: false
  migration_strategy_unresolved: false
  data_integrity_semantics_unresolved: false
  domain_critical_behavior_unresolved: false
  concurrency_semantics_unresolved: false
  deployment_runtime_safety_unresolved: false
  resource_capacity_semantics_unresolved: false
  irreversible_operation_unresolved: false
  repeated_failure: false

review_risk:
  public_contract_material_change: false
  schema_or_migration_touched: false
  auth_or_permission_touched: false
  security_boundary_touched: false
  data_integrity_or_loss_risk: false
  domain_critical_logic_touched: false
  concurrency_or_transaction_touched: false
  irreversible_operation_touched: false
  new_dependency_or_protocol_material: false
  deployment_or_runtime_safety_touched: false
  resource_exhaustion_or_capacity_risk: false
  weak_test_oracle: false
  generated_or_shared_artifact_material: false
  repeated_failure_or_flaky: false

active_contracts:
  - id: TASK-001
    contract_hash: sha256:...
    snapshot_exclude: []

write_guard:
  baseline_created: true
  writer_lock_task_id: TASK-001
  last_write_set_result: passed | failed | not_run

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
- Every important observed fact points to evidence.
- For an architect call, send unresolved decision flags and only the evidence needed to resolve them.
- For a reviewer call, send the final patch, actual material review-risk flags, contracts by id/hash,
  write-guard evidence, and verification results.
- Do not send full patch plus full source files by default. Start with the patch and let Sol read
  targeted surrounding symbols directly.
- If the same Sol thread can safely be reused, prefer reuse; otherwise send a complete versioned packet.
- `public_contract_material_change`, `new_dependency_or_protocol_material`, and
  `generated_or_shared_artifact_material` require semantic/material impact, not mere file churn.
- Security boundaries include secrets, deserialization, SSRF/network trust, cryptography, input
  trust boundaries, and other sensitive data/control flows even when auth itself is unchanged.
- Project-specific financial, numerical, safety, or other domain-critical algorithms should set
  `domain_critical_logic_touched` when a defect could materially change outcomes.
- If a necessary fact is missing, Sol requests a targeted read rather than accepting Terra's framing.
