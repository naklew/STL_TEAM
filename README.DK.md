# SLT Team — DK Cost-Aware Routing

목표는 **Sol의 판단 품질을 유지하면서 Sol이 직접 소비하는 토큰을 최소화**하는 것입니다.

## 권장 운용

부모 Codex 세션:

```text
gpt-5.6-terra
reasoning: high
```

기본 흐름:

```text
Terra reconnaissance / orchestration
        │
        ├─ material decision? ─ yes ─> Sol Architect High
        │                              │
        │                         task contracts
        │                              │
        ├───────────────┬──────────────┤
        ▼               ▼              ▼
   Luna Max         Luna Max       Terra High
 bounded task      bounded task    complex-but-decided
        └───────────────┬──────────────┘
                        ▼
                 Terra integration
                        ▼
              test / lint / typecheck / build
                        ▼
                 Sol Reviewer High
                        ▼
              Luna/Terra bounded repair
```

## 핵심 원칙

- Sol은 코드베이스 탐색을 하지 않는다.
- Sol은 일반 구현을 하지 않는다.
- Sol은 아키텍처/요구사항/인터페이스/보안 판단과 최종 리뷰에 집중한다.
- Sol Max는 자동 사용하지 않는다.
- Luna는 파일 범위와 검증 명령이 명확한 작업에만 사용한다.
- Terra는 탐색, 통합, 테스트, 이미 설계가 확정된 멀티파일 구현을 맡는다.
- 병렬 worker는 기본 1개, 필요 시 2개, 정말 독립적일 때만 3개를 권장한다.

## 설치 후 사용 예시

대상 프로젝트에 `templates/project/.codex/agents/` 내용을 복사하고,
부모 세션을 Terra High로 시작한 뒤:

```text
$sol-luna-team 이 기능을 구현해줘.
Sol은 설계 판단과 최종 리뷰에만 사용하고,
구현과 검증은 Luna/Terra로 처리해.
```

## Sol Max 수동 승격 조건

다음처럼 High로도 해결하기 어려운 고영향 문제에 한정:

- 시스템 아키텍처 변경
- 데이터 모델/스키마 마이그레이션
- 보안 경계 설계
- 복합 race condition / concurrency bug
- 여러 원인 후보가 끝까지 남는 고난도 장애 분석
