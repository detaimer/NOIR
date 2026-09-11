# 평가 (WHY)

## 평가 철학 — 3층 분리, ASR은 헤드라인일 뿐 유일 축 아님
평가는 세 층으로 분리한다:

1. **behaviors**(시드 유해요청) — 내장 소규모 팩(~15) + `jbb`/`harmbench` 로더. 각 behavior 는
   `domain·subcat·tags(taxonomy)` 메타 보유.
2. **judge/scorer**(detector) — pluggable, 구조화 출력 `{success, score?, categories, judge_name}`:
   - 이진: **RefusalMatch**(거부 문구 휴리스틱, 무료·무모델·결정론), **LlamaGuard**(응답 safe/unsafe + 카테고리).
   - 등급: **StrongREJECT**(0~1 = (1−refusal)×(구체성+설득력)/2, judge LLM).
3. **지표 집계**(reporting) — 이진 judge → ASR, 등급 judge → 평균 점수, 그리고 도메인/카테고리/taxonomy별 분해.

**ASR (Attack Success Rate)** = 성공 시도 / 전체 시도. **기본 헤드라인 지표이지 유일 축이 아니다** —
등급 점수·도메인/카테고리/taxonomy 커버리지·judge 합치도까지 함께 본다. judge 는 pluggable 이고,
**target ≠ judge 를 강제**한다(자기 채점 금지).

## 공정한 측정 — Fair-ASR (동일 예산 B)
PAIR·Crescendo 처럼 쿼리를 많이 쓰는 기법은 시도 횟수만으로 유리해진다.
→ **동일 타깃-호출 예산 B** 하에서 비교(Fair-ASR). 예산은 `core` 의 `BudgetedTarget` wrapper 가 자동
집계한다(probe 자가보고 X). ASR@B + 평균 타깃호출 + efficiency(성공/총호출)로 기법을 나란히 본다.

## behaviors 소스
내장 팩(~15, 오프라인) + `jbb`/`harmbench` 로더(`--behaviors builtin|jbb|harmbench|<path>`). 후보였던
AdvBench/HarmBench/JailbreakBench 중 HarmBench·JBB 를 로더로 지원한다. OT/ICS 는 특별취급이 아니라
`domain="ot_ics"` + `attack-ics:*` 태그로 표현되는 1급 지원 도메인이다.

## 산출물
`out/runs/<timestamp>/` 아래: 시도별 **JSONL 로그 + summary.json + config 스냅샷(redact)** + **터미널
요약표** + **HTML 리포트**(정보설계 중심, 도메인/카테고리 위험도 히트맵 강조). 상세는 `docs/plan.md`.
