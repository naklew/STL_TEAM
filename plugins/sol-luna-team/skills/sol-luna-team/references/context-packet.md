# Sol context packet

Use this packet whenever a task crosses a Sol decision or review gate. The goal is to avoid both extremes: dumping the whole repository into Sol, or forcing Sol to trust a lossy Terra summary.

```yaml
base_revision: <git sha or working-tree baseline>
original_requirement: <verbatim or minimally normalized user request>

observed_facts:
  - fact: <directly observed behavior/code fact>
    evidence: <file:symbol, command output, or test>

invariants:
  - <behavior or contract that must remain true>

unknowns:
  - <question that materially affects the decision>

decisions_already_made:
  - <decision and source>

relevant_files:
  - path: src/example.py
    symbols:
      - ExampleClass.method
    reason: Owns the public behavior under discussion.

alternative_designs:
  - option: <candidate>
    evidence_for: <short evidence>
    evidence_against: <short evidence>

rejected_alternatives:
  - option: <candidate>
    reason: <why rejected>

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

active_task_contracts:
  - <task id>

diff_or_patch: <relevant diff, or precise paths if Sol can read them directly>

verification:
  - command: <exact command>
    result: passed | failed | not_run
    evidence: <short output or failure reference>

risk_notes:
  - <anything not captured by booleans>
```

## Rules

- Preserve the original requirement; do not silently rewrite product intent.
- Every important claim in `observed_facts` should point to evidence.
- Sol should directly inspect the listed contract/interface/test files when they are material to the decision.
- If the packet is missing a necessary fact, Sol may request a targeted read rather than accepting Terra's framing.
- Do not include unrelated repository files merely for completeness.
