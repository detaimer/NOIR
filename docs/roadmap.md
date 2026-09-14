# 로드맵 (WHY)

> 이 문서는 **전체 이정표**(모든 사이클의 지도)다. 각 사이클의 상세 task 는 별도 `plan*.md` 에 있고,
> 활성 사이클을 여기서 가리킨다. (WHY 는 roadmap → HOW 는 plan)

## v0.1 — 스캐폴딩 (완료)
역할별 폴더 구조 + 얇은 CLAUDE.md + references/docs + TDD 인프라 + `rt` 진입점. 테스트 green.

## v0.2 — 기능 MVP (완료) → 상세 **[docs/plan.md](plan.md)** (M0~M15)
pluggable 범용 프레임워크(garak/PyRIT류). 요지:
- 기법 3 tier: 정적 one-shot(past-tense·base64·FlipAttack·many-shot) + PAIR + Crescendo
- detector 3개: RefusalMatch · LlamaGuard · StrongREJECT (구조화 출력; ASR은 기본 헤드라인일 뿐 유일 축 아님)
- 어댑터: HTTP(상업+로컬) + Manual · YAML run-config · Fair-ASR · JSONL+터미널+HTML 리포트
- probe/adapter/detector 인터페이스(ABC) + import-linter 계약
- OT/ICS는 `domain`+taxonomy 태그 도메인(하드 특화 X)

## v0.3+ — 발전 지형도 (Level 0)

MVP 직후 돌린 **실모델 측정 타당도 검증**에서, 기본 헤드라인 지표가 무해 요청에 FPR 90~97%로
"거부 안 함"을 "탈옥"으로 세는 문제가 드러났다(상세: 검증 산출물 `out/validation/**`). 그래서
다음 사이클들은 **"측정을 믿게 만들기"를 토대로** 순서를 잡는다.

| Track | 주제 | 요지 | 순서 근거 |
|---|---|---|---|
| **1** | **측정을 믿게 만든다 (측정 타당도·재현성)** | harm-conditioned judge 기본화 · judge↔objective 정합 · 무해 대조군 표준 편입 · judge 캘리브레이션(FPR/FNR) · seed/temperature 노출 · Wilson CI | **1순위** — 이게 안 되면 나머지 수치가 다 오염 |
| **2** | **자극/데이터셋 확대** | JBB/HarmBench 전체 로딩, 시드 팩 확대, 도메인 다양성 | 측정이 믿긴 뒤 잴 대상을 늘림 |
| **3** | **기법 확장** | 새 기법 구현(TAP 등)이 먼저, 플러그인 배관(데코레이터 자동등록·엔트리포인트·preflight, [pluggable-techniques.md](pluggable-techniques.md))은 규모 커지면 | 지금 `PROBES` 한 줄 추가로 충분 — 배관은 규모의 문제 |
| **4** | **UI/UX** | ① 인터랙티브 HTML 리포트(서버 없이 JS만, threshold 슬라이더로 ASR 재계산·필터·judge 비교) 먼저 ② 풀 웹 대시보드는 나중 | 측정이 믿긴 뒤라야 UI에 뜨는 숫자가 진짜 |
| **5** | **런타임 인프라** | LiteLLM · 병렬/async 실행 · retry/backoff | "느려서 불편"할 때 |

의존: **1 → 2 → 3 → (4·5는 병렬 가능)**. 각 Track 착수 시 상세 계획을 별도 `plan-v0.x.md` 로 승격한다
(v0.2 를 plan.md 로 가리켰던 것과 동일 패턴).

### 활성 사이클
- **v0.3 = Track 1 (측정을 믿게 만든다)** → 상세 **[docs/plan-v0.3.md](plan-v0.3.md)**

> 비고: judge 앙상블·멀티모달(FigStep)·OT 전용 대량 데이터셋 저작 등은 위 Track 들에 흡수되거나
> 후속 사이클에서 별도 승격한다.
