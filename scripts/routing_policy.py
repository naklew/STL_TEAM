#!/usr/bin/env python3
"""Deterministic mapping from already-classified SLT flags to model routing.

Semantic classification is still performed by Terra/user evidence. Once the
classification document is supplied, this tool deterministically maps it to
named Sol/Luna/Terra agents.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from policy_defs import BOUNDED_REASONING, DECISION_FLAGS, POLICY_VERSION, REVIEW_FLAGS, TASK_CLASSES


class PolicyError(Exception):
    pass


def validate_flags(name: str, value: Any, keys: tuple[str, ...]) -> None:
    if not isinstance(value, dict):
        raise PolicyError(f"{name} must be an object")
    missing = set(keys) - set(value)
    extra = set(value) - set(keys)
    if missing:
        raise PolicyError(f"{name} missing keys: {', '.join(sorted(missing))}")
    if extra:
        raise PolicyError(f"{name} unknown keys: {', '.join(sorted(extra))}")
    bad = [key for key in keys if not isinstance(value[key], bool)]
    if bad:
        raise PolicyError(f"{name} values must be boolean: {', '.join(bad)}")


def route(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("policy_version") != POLICY_VERSION:
        raise PolicyError(f"policy_version must be {POLICY_VERSION}")
    decision = data.get("decision_gate")
    review = data.get("review_risk")
    execution = data.get("execution")
    validate_flags("decision_gate", decision, DECISION_FLAGS)
    validate_flags("review_risk", review, REVIEW_FLAGS)
    if not isinstance(execution, dict):
        raise PolicyError("execution must be an object")

    task_class = execution.get("task_class")
    if task_class not in TASK_CLASSES:
        raise PolicyError(f"execution.task_class must be one of: {', '.join(TASK_CLASSES)}")
    reasoning = execution.get("bounded_reasoning")
    if task_class == "bounded" and reasoning not in BOUNDED_REASONING:
        raise PolicyError("bounded tasks require execution.bounded_reasoning=mechanical|logic")
    if task_class != "bounded" and reasoning not in (None, ""):
        raise PolicyError("execution.bounded_reasoning is only valid for bounded tasks")

    architect_required = any(decision.values())
    reviewer_required = any(review.values())
    if task_class == "trivial":
        implementation_agent = "parent_terra"
    elif task_class == "bounded":
        implementation_agent = "luna_fast" if reasoning == "mechanical" else "luna_worker"
    else:
        implementation_agent = "terra_worker"

    return {
        "policy_version": POLICY_VERSION,
        "architect_required": architect_required,
        "architect_agent": "sol_architect" if architect_required else None,
        "implementation_agent": implementation_agent,
        "reviewer_required": reviewer_required,
        "reviewer_agent": "sol_reviewer" if reviewer_required else None,
        "decision_reasons": [key for key, value in decision.items() if value],
        "review_reasons": [key for key, value in review.items() if value],
    }


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PolicyError(str(exc)) from exc
    if not isinstance(data, dict):
        raise PolicyError("classification document must be a JSON object")
    return data


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True)
    p.add_argument("--compact", action="store_true")
    args = p.parse_args()
    try:
        result = route(load(Path(args.input)))
    except PolicyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")) if args.compact else json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
