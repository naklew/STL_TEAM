#!/usr/bin/env python3
"""Validate SLT package structure and version alignment without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_AGENTS = {
    "luna-fast.toml": ("luna_fast", "gpt-5.6-luna", "high"),
    "luna-worker.toml": ("luna_worker", "gpt-5.6-luna", "max"),
    "terra-worker.toml": ("terra_worker", "gpt-5.6-terra", "high"),
    "sol-architect.toml": ("sol_architect", "gpt-5.6-sol", "high"),
    "sol-reviewer.toml": ("sol_reviewer", "gpt-5.6-sol", "high"),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    versions = load_json(ROOT / "slt-version.json")
    plugin = load_json(ROOT / "plugins/sol-luna-team/.codex-plugin/plugin.json")
    marketplace = load_json(ROOT / ".agents/plugins/marketplace.json")
    load_json(ROOT / "schemas/task-contract.schema.json")
    load_json(ROOT / "schemas/routing-classification.schema.json")
    cases = load_json(ROOT / "evals/routing-cases.json")

    if plugin.get("version") != versions.get("plugin_version"):
        fail("plugin.json version does not match slt-version.json")
    if plugin.get("skills") != "./skills/":
        fail("plugin skills path must be ./skills/")
    if not marketplace.get("plugins"):
        fail("marketplace.json has no plugin entry")
    if not isinstance(cases, list) or not cases:
        fail("routing eval matrix is empty")

    agent_dir = ROOT / "templates/project/.codex/agents"
    actual = {p.name for p in agent_dir.glob("*.toml")}
    expected = set(EXPECTED_AGENTS)
    if actual != expected:
        fail(f"agent file set mismatch expected={sorted(expected)} actual={sorted(actual)}")
    if (agent_dir / "terra-orchestrator.toml").exists():
        fail("child terra orchestrator must not exist")

    for filename, (name, model, effort) in EXPECTED_AGENTS.items():
        with (agent_dir / filename).open("rb") as f:
            data = tomllib.load(f)
        for field in ("name", "description", "developer_instructions"):
            if not data.get(field):
                fail(f"{filename} missing {field}")
        if data.get("name") != name or data.get("model") != model or data.get("model_reasoning_effort") != effort:
            fail(f"{filename} model/name/effort mismatch")

    with (ROOT / "templates/project/.codex/config.toml").open("rb") as f:
        config = tomllib.load(f)
    agents = config.get("agents", {})
    if agents.get("enabled") is not True or agents.get("max_concurrent_threads_per_session") != 2:
        fail("project agent config mismatch")
    if "default_subagent_model" in agents:
        fail("default_subagent_model must remain unset")

    skill = (ROOT / "plugins/sol-luna-team/skills/sol-luna-team/SKILL.md").read_text(encoding="utf-8")
    if not skill.startswith("---\n") or "name: sol-luna-team" not in skill[:500]:
        fail("SKILL.md frontmatter missing")

    required = [
        ROOT / "scripts/contract_guard.py",
        ROOT / "scripts/routing_policy.py",
        ROOT / "scripts/slt_setup.py",
        ROOT / "scripts/run_policy_eval.py",
        ROOT / "scripts/run_guard_eval.py",
    ]
    for path in required:
        if not path.is_file():
            fail(f"missing script: {path.relative_to(ROOT)}")

    print("PASS repository validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
