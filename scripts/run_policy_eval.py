#!/usr/bin/env python3
"""Run deterministic routing-policy scenario evals."""

from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from routing_policy import PolicyError, route  # noqa: E402


def main() -> int:
    cases_path = SCRIPT_DIR.parent / "evals" / "routing-cases.json"
    cases = json.loads(cases_path.read_text(encoding="utf-8"))
    failures = []
    for case in cases:
        name = case["name"]
        try:
            actual = route(case["input"])
        except PolicyError as exc:
            failures.append((name, f"PolicyError: {exc}"))
            continue
        expected = case["expected"]
        subset = {key: actual.get(key) for key in expected}
        if subset != expected:
            failures.append((name, f"expected={expected} actual={subset}"))
        else:
            print(f"PASS {name}")
    if failures:
        for name, detail in failures:
            print(f"FAIL {name}: {detail}", file=sys.stderr)
        return 1
    print(f"PASS {len(cases)} routing cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
