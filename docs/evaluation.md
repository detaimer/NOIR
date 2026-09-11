# 평가: ASR (WHY)

## 정의
**ASR (Attack Success Rate)** = 성공한 공격 시도 수 / 전체 공격 시도 수.
MVP 는 ASR 하나만 평가 지표로 둔다.

## 공정한 측정 (권고)
BoN·TAP·X-Teaming 처럼 쿼리를 많이 쓰는 기법은 시도 횟수만으로 유리해진다.
→ **동일 타깃-쿼리 예산(fixed target-query budget)** 하에서 ASR 을 비교(Fair-ASR).

## 성공 판정(judge) 종류 — 구체 선정은 다음 대화
- **휴리스틱**: 거부 문구/정규식 매칭. 비용 0, 결정론적, 정밀도 낮음.
- **LLM-judge**: 판정 모델이 유해성/응낙을 채점. 정밀하나 비용·비결정.
- 표준 behaviors 셋 후보: AdvBench, HarmBench, JailbreakBench(JBB, 100 behaviors).

## 산출물
`out/runs/<timestamp>/` 아래에 시도 로그 + ASR 요약(리포트). 형식은 프로젝트 단계에서 확정.
