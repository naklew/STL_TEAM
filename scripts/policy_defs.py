"""Shared SLT Hybrid v0.4.0 policy constants."""

POLICY_VERSION = "0.4.0"
AGENT_BUNDLE_VERSION = "0.4.0"

DECISION_FLAGS = (
    "unresolved_architecture",
    "ambiguous_requirement",
    "competing_root_causes",
    "contract_expansion_required",
    "unresolved_security_policy",
    "security_boundary_unresolved",
    "external_contract_unknown",
    "migration_strategy_unresolved",
    "data_integrity_semantics_unresolved",
    "domain_critical_behavior_unresolved",
    "concurrency_semantics_unresolved",
    "deployment_runtime_safety_unresolved",
    "resource_capacity_semantics_unresolved",
    "irreversible_operation_unresolved",
    "repeated_failure",
)

REVIEW_FLAGS = (
    "public_contract_material_change",
    "schema_or_migration_touched",
    "auth_or_permission_touched",
    "security_boundary_touched",
    "data_integrity_or_loss_risk",
    "domain_critical_logic_touched",
    "concurrency_or_transaction_touched",
    "irreversible_operation_touched",
    "new_dependency_or_protocol_material",
    "deployment_or_runtime_safety_touched",
    "resource_exhaustion_or_capacity_risk",
    "weak_test_oracle",
    "generated_or_shared_artifact_material",
    "repeated_failure_or_flaky",
)

TASK_CLASSES = ("trivial", "bounded", "complex_decided")
BOUNDED_REASONING = ("mechanical", "logic")
