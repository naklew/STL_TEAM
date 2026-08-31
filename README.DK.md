# SLT Hybrid v2 — Cost-Aware Codex Team

목표는 **Sol의 판단 품질을 중요한 지점에만 사용하면서 Sol 사용량과 재작업을 함께 줄이는 것**입니다.

이 버전은 원본 SLT의 plugin 패키징/Task Contract 장점과 Terra-parent 비용 라우팅을 결합합니다.

## 권장 구조

부모 Codex 세션:

```text
gpt-5.6-terra
reasoning: high
```

흐름:

```text
Terra High parent
    │
    ├─ reconnaissance / evidence index
    ├─ objective risk flags
    │      │
    │      ├─ material risk → Sol Architect High
    │      └─ frozen/routine → contract directly
    │
    ├─ Luna Max: narrow bounded implementation
    ├─ Terra High: already-decided multi-file implementation
    │
    ├─ Terra integration + verification
    │
    └─ risk-based Sol Reviewer High
           ├─ high-risk / Sol-designed → mandatory
           ├─ routine medium → conditional
           └─ trivial low-risk → skip
```

## 원칙

- 부모 orchestration은 Terra High가 직접 수행합니다. `terra_orchestrator` child는 사용하지 않습니다.
- Sol은 저장소 전체를 다시 탐색하거나 일반 코딩을 하지 않습니다.
- Sol decision gate는 자연어 감각이 아니라 `risk_flags`를 기준으로 강제합니다.
- Sol에는 단순 요약이 아니라 구조화된 context packet과 필요한 원문 파일/심볼을 제공합니다.
- Luna는 반드시 `luna_worker`로 명시 호출하며, 좁고 독립 검증 가능한 작업에만 사용합니다.
- Terra worker는 설계가 이미 확정된 멀티파일 구현과 focused repair에 사용합니다.
- Sol Max는 자동 승격하지 않습니다.
- shared workspace writer는 기본 1개입니다. 독립성이 명확할 때만 2개까지 허용합니다.
- `allowed_files`는 sandbox ACL이 아니므로 작업 전후 diff로 계약 외 변경을 검증합니다.

## Mandatory Sol risk flags

다음과 같은 위험이 있으면 Sol decision gate를 통과해야 합니다.

- public contract/API/interface 변경
- schema/migration/persistence 변경
- auth/permission/trust boundary
- concurrency/transaction/idempotency/race/order
- irreversible/destructive operation
- new dependency/protocol/framework
- ambiguous acceptance criteria
- multiple plausible root causes
- contract expansion
- repeated/flaky/non-deterministic failure
- weak test oracle / test bypass 의심
- cross-task/release 영향이 있는 generated/shared artifact

제품 선택이나 사용자 승인이 필요한 문제는 Sol이 대신 결정하지 않고 사용자에게 질문합니다.

## Context packet

Sol 호출 시 `references/context-packet.md` 형식을 사용합니다.

핵심 필드:

```yaml
base_revision:
original_requirement:
observed_facts:
invariants:
unknowns:
decisions_already_made:
relevant_files:
alternative_designs:
risk_flags:
active_task_contracts:
diff_or_patch:
verification:
```

Terra의 요약만 믿게 하지 않고, 중요한 계약/인터페이스/테스트/변경 파일은 Sol이 직접 확인할 수 있게 합니다.

## 설치

```bash
codex plugin marketplace add naklew/STL_TEAM --ref hybrid-v2
codex plugin add sol-luna-team@sol-luna-team
```

대상 프로젝트에 다음도 복사합니다.

```text
templates/project/.codex/agents/  →  <target>/.codex/agents/
templates/project/.codex/config.toml → <target>/.codex/config.toml
```

그 후 새 Terra High 세션에서 명시적으로 호출합니다.

```text
$sol-luna-team 이 기능을 구현해줘.
```

## Agent 구성

```text
sol-architect.toml  → Sol High / read-only
sol-reviewer.toml   → Sol High / read-only
luna-worker.toml    → Luna Max / workspace-write
terra-worker.toml   → Terra High / workspace-write
```

이름 없는 subagent가 Luna로 떨어지는 것을 방지하기 위해 global/default Luna 모델은 지정하지 않습니다.

## 파일

- `plugins/sol-luna-team/skills/sol-luna-team/SKILL.md`: 전체 routing/orchestration 정책
- `references/task-contract.md`: bounded task 계약
- `references/context-packet.md`: Sol 전달용 구조화 evidence packet
- `templates/project/.codex/config.toml`: 프로젝트별 concurrency 제한
- `.agents/plugins/marketplace.json`: repo-local marketplace
- `plugins/sol-luna-team/.codex-plugin/plugin.json`: installable plugin manifest

## 설계 목표

이 시스템은 총 토큰 자체의 최소화보다 다음을 최적화합니다.

```text
Sol token usage + avoidable rework
```

Luna/Terra에 맡긴 작업이 반복 실패하거나 새로운 설계 판단이 생기면 저가 모델로 계속 재시도하지 않고 Sol gate로 되돌립니다.
