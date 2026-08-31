#!/usr/bin/env python3
"""Run compact deterministic routing-policy scenario evals."""

from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from policy_defs import DECISION_FLAGS, POLICY_VERSION, REVIEW_FLAGS  # noqa: E402
from routing_policy import PolicyError, route  # noqa: E402


def main() -> int:
    cases = json.loads((SCRIPT_DIR.parent / "evals" / "routing-cases.json").read_text(encoding="utf-8"))
    failures = []
    for case in cases:
        decision = {key: False for key in DECISION_FLAGS}
        review = {key: False for key in REVIEW_FLAGS}
        for key in case.get("decision_true", []):
            decision[key] = True
        for key in case.get("review_true", []):
            review[key] = True
        payload = {
            "policy_version": POLICY_VERSION,
            "decision_gate": decision,
            "review_risk": review,
            "execution": case["execution"],
        }
        try:
            actual = route(payload)
        except PolicyError as exc:
            failures.append((case["name"], f"PolicyError: {exc}"))
            continue
        expected = case["expected"]
        subset = {key: actual.get(key) for key in expected}
        if subset != expected:
            failures.append((case["name"], f"expected={expected} actual={subset}"))
        else:
            print(f"PASS {case['name']}")
    if failures:
        for name, detail in failures:
            print(f"FAIL {name}: {detail}", file=sys.stderr)
        return 1
    print(f"PASS {len(cases)} routing cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
