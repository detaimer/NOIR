# redteam v0.3 — Track 1: 측정을 믿게 만든다 (구현 계획)

> 이 문서 = v0.3 사이클(Track 1) 구현 계획 (git 관리). 로드맵 연결: `docs/roadmap.md`(전체 지도).
> 이전 사이클: `docs/plan.md`(v0.2 MVP, 완료). 설계 근거: `docs/evaluation.md`, `docs/architecture.md`.
> 작업 규칙: `references/`, `.claude/rules/tdd.md`.

## Context (왜 지금 이걸 하나)

MVP(M0–M15, `docs/plan.md`) 구현·검증이 끝났다. 직후 로컬 Ollama 로 돌린 **실모델 측정 타당도 검증**
(8 run·타깃호출 ~200, 산출물 `out/validation/**` — gitignored)에서 도구가 뱉는 숫자의 신뢰성 문제가
드러났다:

- 기본 헤드라인 지표 `refusal_match` 의 **무해 요청 FPR = 90~97%** (쿠키 레시피·여행일정에도 "탈옥 성공").
  `refusal_match` 는 정의상 "거부 문구가 없으면 성공"이라(`src/redteam/detectors/refusal_match.py`), 응답만
  하면 success 다.
- 정적 기법(past_tense/flip/base64/many_shot)은 **precision ≈ 0** — 8B 타깃의 실제 응답이 대부분
  decode-only·오역("피싱"→"fishing")·역사 개괄이라 operational 유해물이 사실상 없었다.
- 진짜 탈옥은 **PAIR(dolphin3)** 에서만 재현됐고, 그때만 judge 3종이 합의했다(construct validity 신호).
- judge 마다 채점 대상이 달라 같은 응답을 다르게 판정한다: 멀티턴(crescendo)에서 `llama_guard`/
  `strong_reject` 는 **마지막 순한 질문**(`final_prompt`)을, `crescendo_objective`/`pair_judge` 는 **실제
  objective** 를 본다.
- 어댑터가 `temperature/seed/timeout/max_tokens` 를 안 보내 **재현 불가**(같은 config 재실행 시 ASR 이
  1.0↔0.5 로 튐), behavior 3~6개라 **검정력 없음**(Fisher p≈0.10).

결론: **기능을 더 얹기 전에 "측정을 믿게 만드는" 것이 먼저다.** 지표가 안 믿기면 기법·데이터셋을
늘려도 오염된 숫자가 늘 뿐이다. (전체 순서는 `docs/roadmap.md` v0.3+ Track 1~5 참조. 이 문서는 Track 1.)

전제(v0.2 와 동일): 전역 TDD 훅 — impl `<name>.py` 는 `tests/test_<name>.py` 선행, 매 `.py` 쓰기 후 전체
pytest green, 모듈 basename repo 전역 유일, 비결정(LLM/네트워크) 로직은 ABC/Protocol 뒤 + fake 테스트,
실 API 호출은 `live` marker 로 기본 제외.

## Goal (Definition of Done)

`rt` 가 보고하는 ASR 이 "거부 안 함"이 아니라 **실제 탈옥**을 반영하고, 무해 요청 오탐률(FPR)과
신뢰구간을 **매 실행에서 함께** 보여주며, 같은 config 를 **재현**할 수 있다. 구체적 Done:

- (a) 유해+무해 혼합 실행 시 리포트가 **ASR(harmful)과 FPR(benign)을 분리 표시**.
- (b) judge 캘리브레이션 결과(judge별 **FPR/FNR/precision/κ**)를 라벨 fixture 대비 산출.
- (c) run 이 쓴 sampling 파라미터(temperature/seed/max_tokens/timeout)가 **config 스냅샷에 기록**되고,
  동일 seed 재실행이 가능(백엔드 seed 지원 범위 내).
- (d) ASR/FPR 에 **Wilson score 신뢰구간** 병기.
- 전 구간 fake 로 결정론 테스트 green, `ruff`/`import-linter`/`deptry` clean.

## 확정된 설계 결정 (인터뷰 완료)

- **기본 primary = `llama_guard` 단독** — 검증에서 무해 FPR 3%로 가장 낮음. `refusal_match` 는 보조
  detector 로 유지(비교·오프라인 재계산용). *(로컬엔 진짜 llama-guard 체크포인트가 없어 일반 모델에
  guard 프롬프트를 쓰는 형태 — 정식 `llama-guard3` 를 받으면 판정 품질이 더 오름.)*
- **재현성 = 노출+기록만** — sampling 파라미터를 config→payload→snapshot 으로 흘린다. 미지정 시 현행과
  동일 동작. **결정론 replay 는 보장하지 않는다**(로컬 Ollama 등이 seed 를 무시할 수 있어 못 지킬 약속).
- **무해 대조군 = `Behavior.label`(harmful|benign, 기본 harmful)** — 별도 source 가 아니라 필드. 한 run 에
  유해+무해를 섞어 돌리면 라벨별로 분리 집계. 하위호환(기존 behavior 는 harmful).
- **캘리브레이션 = 씨앗 fixture 포함** — 검증에서 손라벨한 표본(~78건)을 라벨 fixture 로 만들어 judge별
  혼동행렬을 낸다. **대규모 라벨링 캠페인은 비목표**(씨앗 수준만).

## Requirements

1. **harm-conditioned judge 를 기본 primary 로** — 기본 detector 스택의 [0]을 `llama_guard` 로.
   `refusal_match` 는 보조로 남긴다.
2. **judge↔objective 정합** — 멀티턴에서 harm judge 가 `final_prompt` 가 아니라 behavior 의 실제
   objective 를 채점하도록 detector 호출 경로를 고친다(`runner._score_extra_judges` 등).
3. **무해 대조군을 표준 입력으로** — `Behavior.label` 추가 + 로더 보존 + 내장 benign 팩. 검증용
   `benign10.jsonl` 을 정식 대조군 팩으로 편입.
4. **ASR/FPR 분리 집계** — `aggregate.summarize` 가 label 별로 ASR(harmful)·FPR(benign)을 나눠 낸다.
5. **judge 캘리브레이션 도구** — 라벨 fixture 대비 judge별 FPR/FNR/precision/κ 산출(오프라인, 타깃 재호출 X).
6. **재현성** — `HttpOpenAIAdapter` 에 sampling 파라미터 노출 + config 필드 + 스냅샷 기록(비밀키 redact 유지).
7. **통계** — ASR/FPR 에 Wilson score 신뢰구간 병기(터미널표·HTML).

## Non-goals (이 사이클에서 안 함)

새 공격 기법(TAP 등) · 플러그인 배관(데코레이터/엔트리포인트/preflight) · 풀 웹 대시보드 · LiteLLM/async ·
멀티모달 · 데이터셋 auto-download · 대규모 라벨링 캠페인. (→ 각각 Track 2~5, `docs/roadmap.md`)

## Tasks (TDD 순서·의존성 순)

> 각 task: `tests/test_<name>.py` 먼저(상단 `importorskip` 브레이커) → impl → `pytest -q` green + `ruff`.

1. [ ] **sampling 파라미터 노출** — `test_http_openai` 확장 → `HttpOpenAIAdapter(temperature, seed,
   max_tokens, timeout)` 가 payload 에 반영, 미지정 시 키 생략. 완료조건: fake client 로 payload assert,
   네트워크 X. · 검증: 단위테스트.
2. [ ] **config 에 sampling + 스냅샷 기록** — `core/config_schema.py`/`config_loader.py` 에 sampling 필드,
   redact 규칙 유지. 완료조건: yaml→RunConfig 왕복 + 스냅샷에 값 존재·비밀키 부재. · 검증: 단위테스트.
3. [ ] **Behavior.label + benign 팩** — `core/records.py` `Behavior` 에 `label`(기본 "harmful"),
   `behaviors/loaders.py` 가 보존, 내장 benign 팩 추가. 완료조건: 유해+무해 혼합 로드·라벨 보존.
   · 검증: `test_records`/`test_loaders` 확장.
4. [ ] **summarize ASR/FPR 분리** — `reporting/aggregate.py` `summarize` 가 label 별 분리 집계(harmful→ASR,
   benign→FPR). 완료조건: 수제 attempts→정확 수치, 하위호환(라벨 없으면 종전과 동일). · 검증: `test_aggregate`.
5. [ ] **Wilson CI** — `reporting/aggregate.py` 에 Wilson score 구간 헬퍼 + `Summary` 병기. 완료조건:
   알려진 (성공, 시행)→알려진 구간. · 검증: `test_aggregate`(또는 신규 `test_wilson`).
6. [ ] **judge↔objective 정합** — 멀티턴에서 harm judge 입력을 objective 로. 완료조건: crescendo attempt 에서
   judge 가 받은 prompt 가 objective 임을 assert + 정적 경로 무회귀. · 검증: `test_runner`/detector 테스트.
7. [ ] **기본 primary 전환** — 기본 detector 스택 [0]=`llama_guard`, `examples/run.yaml`·docs 갱신.
   완료조건: 기본 실행이 llama_guard 헤드라인. · 검증: `test_config_loader`/`test_cli`.
8. [ ] **judge 캘리브레이션 도구** — 라벨 fixture 대비 FPR/FNR/precision/κ 산출(오프라인). 완료조건:
   씨앗 fixture 로 알려진 혼동행렬. · 검증: 신규 `tests/test_calibration.py`(가칭).
9. [ ] **리포팅 반영** — 터미널표·HTML 에 FPR·CI 표시 + 판정 척도 병기(0~1 vs 1~10 혼재 해소).
   완료조건: 섹션·값 렌더, autoescape 유지. · 검증: `test_terminal_table`/`test_html_report`.

## Verification (end-to-end)

```bash
python -m pytest -q && ruff check . && ruff format --check .
lint-imports && deptry src
# 유해+무해 혼합 실행 → 리포트에 ASR·FPR·CI 동시 표시, 스냅샷에 sampling 기록
rt run -c <cfg: harmful+benign behaviors, primary=llama_guard, seed 고정>
# 동일 seed 재실행이 (백엔드 seed 지원 범위 내에서) 재현되는지 스냅샷 diff 로 확인
# judge 캘리브레이션: 라벨 fixture 대비 judge별 FPR/FNR/precision 출력
```

## 검증 근거 (out/validation, 참고)

이 계획의 수치 근거는 MVP 직후 검증 run 들(gitignored `out/validation/**`). 핵심: benign FPR
refusal_match 90~97% / strong_reject 33~37% / llama_guard 3~10%; PAIR(dolphin3) 3/3 진짜 탈옥,
정적 precision≈0; 어댑터 재실행 비결정성(ASR 1.0↔0.5). 재현 방법은 그 디렉터리의 `analyze.py` 참조.
