# SLT Hybrid Cost-Aware Team v0.4.0

목표는 **Sol의 판단 품질을 필요한 지점에만 사용하고, 탐색·구현·검증 토큰은 Terra/Luna로 이동**하는 것입니다.

v0.4.0은 v0.3.0의 비용 라우팅에 실제 실행 안전장치를 더했습니다.

## 핵심 구조

```text
Terra High Parent
       │
       ├─ trivial fast path -> Terra 직접 처리
       │
       └─ non-trivial
             │
      semantic classification
             │
      decision_gate / review_risk
             │
      deterministic routing_policy.py
             │
      unresolved decision? -> Sol Architect High
             │
        task contract JSON
             │
     worktree writer lock
             │
   contract hash + protected baseline
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
        material risk? -> Sol Reviewer High
```

## v0.4.0 핵심 변경

### 1. Worktree-safe setup

Codex/Git linked worktree처럼 `.git`이 파일인 환경에서도 `git rev-parse --git-path`를 사용해
실제 Git metadata 경로를 찾습니다.

```bash
python scripts/slt_setup.py install /path/to/project
python scripts/slt_setup.py status /path/to/project
python scripts/slt_setup.py update /path/to/project
```

설치 시 관리 파일/config/Git exclude 내용을 먼저 준비한 뒤 atomic replace를 사용합니다.
실패 시 기존 내용을 복원하도록 설계했습니다.

`status`는 다음을 검사합니다.
- plugin/policy/agent bundle version
- named agent/tool 파일 hash drift
- `.codex/config.toml`의 `[agents]` 설정
- worktree-safe Git `info/exclude` 설정

### 2. Ignored 파일까지 write-set 검증

v0.3.0은 tracked + non-ignored untracked 파일만 실질적으로 보호했습니다.
v0.4.0은 다음을 snapshot합니다.

- tracked files
- non-ignored untracked files
- ignored untracked files (`.env`, ignored local config, generated outputs 등)

따라서 pre-existing ignored 파일 내용 변경과 새 ignored 파일 생성도 범위 밖이면 탐지합니다.

거대한 disposable tree는 contract의 `snapshot_exclude`에 명시적으로 넣을 수 있지만,
그 경로는 write guard 보호 대상에서 제외됩니다. 보안/설정/마이그레이션/release artifact는
무심코 제외하면 안 됩니다.

### 3. Protected baseline + base_revision 검증

baseline은 더 이상 target workspace의 `.codex/slt-state/`에 저장하지 않습니다.

```text
git rev-parse --git-path slt-baselines/<TASK>.baseline.json
```

형태의 Git metadata 영역에 저장합니다.

`create-task-baseline`은:
- contract `base_revision` == 실제 HEAD
- valid contract hash/version
- matching writer lock

을 요구합니다.

`verify-write-set`은 HEAD가 바뀌거나 contract/hash가 baseline과 달라지면 실패합니다.

### 4. Single-writer lock

같은 worktree에 writer가 동시에 두 개 들어가는 것을 막기 위해:

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id TASK-001
# writer + guard
python .codex/slt-tools/writer_lock.py release --task-id TASK-001
```

를 사용합니다.

lock은 현재 Git worktree의 private gitdir에 있으므로 같은 worktree에서는 writer 1개가
기본 강제됩니다. 병렬 writer가 꼭 필요하면 별도 Git worktree를 사용합니다.

### 5. Sol Architect / Reviewer 분리 + materiality

`decision_gate`는 **아직 해결되지 않은 중요한 결정**만 Sol Architect로 보냅니다.

`review_risk`는 **실제 구현이 material risk domain을 건드렸는지**를 봅니다.

추가된 주요 critical domain:
- security/trust boundary, secret handling, SSRF, deserialization, crypto 등
- data integrity / data loss
- 금융·수치·안전 등 project-specific domain-critical logic
- deployment/runtime safety
- resource exhaustion / capacity risk

그리고 다음은 단순 변경만으로 Sol Reviewer를 부르지 않습니다.
- cosmetic public surface change
- routine lockfile churn
- benign generated snapshot

실제 semantic/compatibility/release 영향이 있을 때만 `*_material*` flag를 true로 설정합니다.

### 6. Luna High / Max 분리

- `luna_fast`: Luna High — 기계적이고 명확한 bounded 작업
- `luna_worker`: Luna Max — 좁지만 로직 reasoning이 필요한 작업
- `terra_worker`: Terra High — 이미 설계가 확정된 복잡/멀티파일 구현

## 중요한 한계

이 시스템은 **완전한 런타임 강제형 AI router가 아닙니다.**

Terra가 evidence를 보고 semantic boolean을 판단하는 단계는 여전히 모델 판단입니다.
코드가 강제하는 것은 그 이후의:

- named-agent routing mapping
- version/hash validation
- writer lock
- base revision validation
- protected baseline
- tracked/untracked/ignored write-set verification

입니다.

즉 정확한 표현은:

> structured semantic classification + deterministic post-classification routing/guards

입니다.

## 설치

```bash
git clone https://github.com/naklew/STL_TEAM.git
cd STL_TEAM

codex plugin marketplace add naklew/STL_TEAM --ref main
codex plugin add sol-luna-team@sol-luna-team

python scripts/slt_setup.py install /path/to/target-project
python scripts/slt_setup.py status /path/to/target-project
```

새 Codex 세션은 `gpt-5.6-terra` + `high`로 시작하고 `$sol-luna-team`을 명시 호출하는 것을 권장합니다.

Plugin만 설치하고 agent bundle을 설치하지 않으면 전체 시스템이 완성되지 않습니다.

## CI / Eval

```bash
python scripts/validate_repo.py
python scripts/run_policy_eval.py
python scripts/run_guard_eval.py
python scripts/run_setup_eval.py
```

GitHub Actions에서도 동일 검증을 실행합니다.

현재 eval에는 다음이 포함됩니다.
- material/non-material routing cases
- security/data-integrity/domain-critical/deployment/capacity risk
- ignored-file mutation/new ignored file
- forbidden/undeclared write
- deletion/rename/symlink/binary mutation
- contract tampering
- stale base revision
- duplicate writer lock
- linked Git worktree setup/status/update

## 운용 원칙

- Sol Max 자동 사용 금지
- 같은 worktree writer 1개
- parallel writer는 별도 worktree
- trivial 작업은 Terra parent가 직접 처리
- 제품 선택/승인은 Sol이 아니라 사용자에게 질문
- Sol에는 전체 repo dump 대신 versioned context packet + patch + 필요한 symbol 원문을 제공
- 총 토큰보다 `Sol token + 재작업`을 최적화
