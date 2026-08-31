# SLT Hybrid Cost-Aware Team v0.4.0

목표는 **Sol의 판단 품질은 중요한 지점에 집중하고, 탐색·구현·검증 토큰은 Terra/Luna로 이동**하는 것입니다.

현재 구조는 Terra High parent가 semantic classification을 수행하고, 그 이후 routing/contract/write-set 검증은 실행 코드로 제한하는 방식입니다.

## 핵심 구조

```text
Terra High Parent
       │
       ├─ trivial fast path -> Terra 직접
       │
       └─ non-trivial
             │
      semantic classification
             │
      deterministic routing_policy.py
             │
 unresolved decision? -> Sol Architect High
             │
        task contract JSON
             │
 workspace-local writer lock
             │
 contract hash + baseline + parent-held SHA seal
             │
   ┌─────────┼──────────┐
   │         │          │
Luna High  Luna Max  Terra High
   └─────────┼──────────┘
             │
 sealed verify-write-set
             │
      Terra integration
             │
 material review risk? -> Sol Reviewer High
```

## 실행 안전장치

### Worktree-safe setup

`git rev-parse --git-path info/exclude`를 사용하므로 일반 checkout과 `.git`이 파일인 linked worktree 모두 지원합니다.

```bash
python scripts/slt_setup.py install /path/to/project
python scripts/slt_setup.py status /path/to/project
python scripts/slt_setup.py update /path/to/project
```

설치/업데이트는 atomic replace와 rollback을 사용하고, `status`는 agent/tool hash, version, `.codex/config.toml`, Git exclude drift를 검사합니다.

### Ignored 파일과 Windows case-only rename

write guard는 다음을 snapshot합니다.

- tracked files
- non-ignored untracked files
- ignored untracked files
- 실제 filesystem directory-entry casing

따라서 ignored `.env`/local config 변경뿐 아니라 Windows의 `foo.txt -> FOO.txt` 같은 case-only rename도 변경으로 취급합니다.

거대한 disposable tree는 contract의 `snapshot_exclude`로 제외할 수 있지만, 제외된 경로는 보호되지 않습니다.

### Codex-writable baseline + parent-held seal

기본 baseline은 외부 `~/.codex`나 `.git`이 아니라:

```text
<target-worktree>/.codex/slt-state/baselines/
```

에 저장됩니다. 이 경로는 일반 Codex `workspace-write`에서 생성 가능한 것을 목표로 합니다.

baseline 생성:

```bash
python .codex/slt-tools/contract_guard.py create-task-baseline \
  --contract <contract.json> --json
```

반환값에는 `baseline`과 `baseline_sha256`이 포함됩니다. **Parent는 SHA seal을 보관하고 worker에게 전달하지 않습니다.**

최종 검증:

```bash
python .codex/slt-tools/contract_guard.py verify-write-set \
  --contract <contract.json> \
  --baseline-sha <PARENT_HELD_BASELINE_SHA256>
```

worker가 workspace-local baseline을 수정하더라도 parent-held seal과 달라지므로 verification이 실패합니다. 이는 tamper-evident cooperative guard이며 pre-write ACL이나 악성 프로세스에 대한 보안 경계는 아닙니다.

`SLT_STATE_HOME`은 명시적으로 다른 writable state root를 쓰고 싶을 때만 선택적으로 사용할 수 있습니다.

### Workspace-local writer lock

```bash
python .codex/slt-tools/writer_lock.py acquire --task-id TASK-001
# writer + guard
python .codex/slt-tools/writer_lock.py release --task-id TASK-001
```

기본 lock은:

```text
<target-worktree>/.codex/slt-state/locks/slt-writer.lock
```

에 저장됩니다. 따라서 `.git` 쓰기 권한에 의존하지 않습니다. 같은 worktree의 cooperating writer는 1개로 제한되고, 별도 Git worktree는 독립 lock을 가집니다.

## Sol routing

`decision_gate`는 **아직 해결되지 않은 중요한 결정**만 Sol Architect로 보냅니다.

`review_risk`는 **실제 구현이 material risk domain을 건드렸는지**를 판단해 Sol Reviewer를 호출합니다.

주요 critical domain:
- auth/permission 및 security/trust boundary
- secret handling, deserialization, SSRF, crypto
- data integrity / data loss
- 금융·수치·안전 등 domain-critical logic
- concurrency / transaction
- migration/schema
- deployment/runtime safety
- resource exhaustion / capacity
- irreversible operation
- external protocol/API compatibility

routine lockfile churn, benign generated snapshot, cosmetic public change는 material risk가 아니면 Sol review를 요구하지 않습니다.

## Worker routing

- `luna_fast`: Luna High — 기계적인 bounded 작업
- `luna_worker`: Luna Max — 좁지만 로직 reasoning이 필요한 작업
- `terra_worker`: Terra High — 설계가 확정된 복잡/멀티파일 구현
- trivial: child 없이 Terra parent 직접 처리

## 중요한 한계

이 시스템은 완전한 런타임 강제형 AI router가 아닙니다. Terra가 semantic boolean을 정하는 단계는 여전히 모델 판단입니다.

코드가 강제하는 것은 그 이후의 routing mapping, version/hash validation, writer lock, base revision validation, baseline seal verification, tracked/untracked/ignored/case-aware write-set 검증입니다.

정확한 표현은:

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

새 Codex 세션은 `gpt-5.6-terra` + `high`로 시작하고 `$sol-luna-team`을 명시 호출하는 것을 권장합니다. Plugin만 설치하면 custom agent bundle은 설치되지 않으므로 setup 단계가 별도로 필요합니다.

## CI / Eval

```bash
python scripts/validate_repo.py
python scripts/run_policy_eval.py
python scripts/run_guard_eval.py
python scripts/run_setup_eval.py
```

GitHub Actions는 **Ubuntu와 Windows**에서 동일 검증을 실행합니다. 현재 guard eval은 ignored-file mutation/new ignored file, forbidden/undeclared write, delete/rename/case-only rename, binary, symlink(플랫폼 지원 시), contract tampering, baseline seal tampering, stale base revision, duplicate writer lock을 다룹니다. Setup eval은 일반 checkout과 linked worktree install/status/update/rollback을 다룹니다.

## 운용 원칙

- Sol Max 자동 사용 금지
- 같은 worktree writer 1개
- parallel writer는 별도 worktree
- trivial 작업은 Terra parent 직접 처리
- 제품 선택/승인은 사용자에게 질문
- Sol에는 전체 repo dump 대신 versioned context packet + patch + 필요한 symbol 원문 제공
- 총 토큰보다 `Sol token + 재작업` 최적화
