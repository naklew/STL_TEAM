# SLT Hybrid Cost-Aware Team v0.3.0

목표는 **Sol의 판단 품질을 필요한 지점에만 사용하고, 탐색·구현·검증 토큰은 Terra/Luna로 이동**하는 것입니다.

## 핵심 구조

```text
Terra High Parent
       │
       ├─ trivial fast path -> Terra 직접 처리
       │
       └─ non-trivial
             │
          의미 분류
             │
      decision_gate / review_risk
             │
      deterministic routing script
        ┌────┴───────────┐
        │                │
  unresolved decision?   │
        │                │
  Sol Architect High     │
        │                │
        └──── contract ──┘
             │
     contract hash + baseline
             │
   ┌─────────┼──────────┐
   │         │          │
Luna High  Luna Max  Terra High
mechanical bounded   complex-decided
   └─────────┼──────────┘
             │
      verify-write-set
             │
      Terra integration
             │
     final review_risk
             │
        risky? -> Sol Reviewer High
```

## v0.3.0에서 바뀐 점

### 1. Architecture gate와 Review risk 분리

`decision_gate`는 **아직 해결되지 않은 설계 판단**만 Sol Architect로 보냅니다.
`review_risk`는 **설계는 이미 확정됐지만 최종 결과를 Sol이 봐야 하는 고위험 변경**을 표시합니다.

예를 들어 이미 정책이 확정된 인증 코드 수정은:

```text
decision_gate = all false
review_risk.auth_or_permission_touched = true
```

이므로 Sol Architect는 생략하고 구현 후 Sol Reviewer만 호출할 수 있습니다.

### 2. Write boundary 실제 검증

`allowed_files`는 여전히 sandbox ACL은 아닙니다. 대신 v0.3.0부터 작업 전후 파일 내용을 실제로 해시해 범위 이탈을 검출합니다.

```bash
python .codex/slt-tools/contract_guard.py hash-contract --contract <contract.json> --write
python .codex/slt-tools/contract_guard.py validate-task-contract --contract <contract.json>
python .codex/slt-tools/contract_guard.py create-task-baseline --contract <contract.json>
# worker 실행
python .codex/slt-tools/contract_guard.py verify-write-set --contract <contract.json>
```

허용되지 않은 파일이 바뀌면 `UNDECLARED`, 금지 파일이면 `FORBIDDEN`으로 실패합니다.
기존 dirty worktree도 파일별 content snapshot을 기준으로 비교합니다.

### 3. Luna High / Max 분리

- `luna_fast`: Luna High — 기계적이고 명확한 bounded 작업
- `luna_worker`: Luna Max — 좁지만 로직 reasoning이 필요한 작업
- `terra_worker`: Terra High — 이미 설계가 확정된 복잡/멀티파일 구현

### 4. 설치·업데이트 버전 동기화

Plugin 설치와 별도로 project custom agents가 필요하므로 setup 도구를 추가했습니다.

```bash
python scripts/slt_setup.py install /path/to/project
python scripts/slt_setup.py status /path/to/project
python scripts/slt_setup.py update /path/to/project
```

대상 프로젝트에는 `.codex/slt-team.json`이 생성되고 policy/agent bundle 버전과 관리 파일 hash가 기록됩니다.
Skill은 v0.3.0 bundle이 없거나 오래된 경우 named worker를 조용히 실행하지 않도록 설계했습니다.

### 5. Routing eval / CI

라우팅 결과는 의미 분류 이후에는 스크립트로 고정됩니다.

```bash
python scripts/run_policy_eval.py
python scripts/run_guard_eval.py
python scripts/validate_repo.py
```

GitHub Actions에서도 동일 검증을 실행합니다.

## 중요한 한계

이 시스템을 **완전 결정론적 AI router**라고 부르면 안 됩니다.

Terra가 코드와 요구사항을 보고 다음 boolean을 판단하는 단계는 여전히 의미 판단입니다.

```text
unresolved_architecture?
auth code touched?
weak test oracle?
```

v0.3.0이 코드로 강제하는 부분은 **그 판단 이후의 routing mapping, contract version/hash, baseline, write-set 검증**입니다.

## 설치

```bash
git clone https://github.com/naklew/STL_TEAM.git
cd STL_TEAM

codex plugin marketplace add naklew/STL_TEAM --ref main
codex plugin add sol-luna-team@sol-luna-team

python scripts/slt_setup.py install /path/to/target-project
```

새 Codex 세션은 `gpt-5.6-terra` + `high`로 시작하고 `$sol-luna-team`을 명시 호출하는 것을 권장합니다.

Plugin만 설치하고 agent bundle을 설치하지 않으면 전체 멀티에이전트 시스템이 완성되지 않습니다.

## 운용 원칙

- Sol Max 자동 사용 금지
- 공유 workspace writer 기본 1개
- trivial 작업은 Terra parent가 직접 처리
- 제품 선택/승인은 Sol이 아니라 사용자에게 질문
- Sol에는 전체 repo dump 대신 versioned context packet + patch + 필요한 symbol 원문을 제공
- 총 토큰보다 `Sol token + 재작업`을 최적화
