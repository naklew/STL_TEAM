# SLT Hybrid v2 — Cost-Aware Codex Team

Terra High를 부모 세션으로 사용하고, Luna Max는 좁고 검증 가능한 구현에, Sol High는 객관적 risk gate와 고위험 최종 리뷰에만 사용하는 Codex 멀티에이전트 구성입니다.

핵심 목표는 **Sol token usage + avoidable rework 최소화**입니다.

자세한 한국어 설명은 [`README.DK.md`](README.DK.md)를 확인하세요.

## 설치

```bash
codex plugin marketplace add naklew/STL_TEAM --ref hybrid-v2
codex plugin add sol-luna-team@sol-luna-team
```

대상 프로젝트에는 `templates/project/.codex/` 내용을 복사하고 새 Terra High 세션에서 `$sol-luna-team`을 명시적으로 호출합니다.

## Routing

```text
Terra High parent
  ├─ objective risk classifier
  │    └─ material risk → Sol Architect High
  ├─ Luna Max → narrow bounded implementation
  ├─ Terra High → already-decided multi-file implementation
  ├─ Terra integration / verification
  └─ risk-based Sol Reviewer High
```

Sol Max는 자동 사용하지 않습니다.

## Origin

This repository is a cost-aware derivative of the MIT-licensed `newrise0410/SLT_Team` orchestration approach, with revised routing, risk gates, context packets, and project-scoped concurrency controls.
