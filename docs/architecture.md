# 아키텍처 (WHY)

## 목표
범용 블랙박스 LLM red-teaming: 타깃(상업 API + 로컬)에 공격 기법을 적용 → 응답 수집 →
성공 판정 → ASR 집계.

## 플러그인 구조 (의도)
역할별 플러그인으로 분리하고 레지스트리로 조합한다.

- `probes/` — 공격 기법. 리서치 결론상 모든 기법은 `{attacker?, judge?, turns, transform}`
  4-필드로 환원된다:
  - 정적 변환(single-turn, attacker 불필요): past-tense, 인코딩(base64/rot13/leetspeak/caesar),
    FlipAttack, DeepInception, many-shot 등
  - LLM 반복형: PAIR, TAP, PAP, GOAT
  - 멀티턴: Crescendo, ActorAttack, X-Teaming
- `adapters/` — 타깃 백엔드. **OpenAI 호환 base_url 하나로 상업 API(키 주입)와
  로컬(Ollama/vLLM) 모두 커버** 가능(LiteLLM 유력).
- `detectors/` — 성공 판정(ASR judge): 휴리스틱(거부 문구/정규식) 또는 LLM-judge.
- `reporting/` — 결과/ASR 리포트.
- `core/` — 플러그인 ABC·레코드 타입·레지스트리 등 공용 기반.
- `cli.py` — `rt` 진입점.

## 레이어 계약 (의도, 프로젝트 단계에서 import-linter 로 강제 예정)

    cli > runner > registry > (probes | adapters | detectors | reporting) > core

`core` 는 다른 레이어에 의존하지 않는다. litellm 등 엔진 의존은 `adapters`/`detectors` 뒤로만.

## 미확정 (다음 대화)
probe/adapter/detector 인터페이스 서명, 기법 batch 선정, judge 종류, behaviors 시드셋.
