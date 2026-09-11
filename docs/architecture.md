# 아키텍처 (WHY)

## 목표
범용 블랙박스 LLM red-teaming: 타깃(상업 API + 로컬 + Manual)에 공격 기법을 적용 → 응답 수집 →
judge 로 성공 판정 → 다축 집계(ASR + 등급 점수 + 도메인/카테고리/taxonomy). ASR 은 기본 헤드라인일 뿐
유일 축이 아니다(→ `docs/evaluation.md`).

## 플러그인 구조 (의도)
역할별 플러그인으로 분리하고 레지스트리로 조합한다.

- `probes/` — 공격 기법. 리서치 결론상 모든 기법은 `{attacker?, judge?, turns, transform}`
  4-필드로 환원되어 단일 `Probe.run(behavior, ctx)` 계약으로 수렴한다:
  - 정적 변환(single-turn, attacker 불필요): past-tense, base64, FlipAttack, many-shot (MVP)
  - LLM 반복형: PAIR (MVP), TAP/PAP/GOAT (v0.2+)
  - 멀티턴: Crescendo (MVP), ActorAttack/X-Teaming (v0.2+)
- `adapters/` — 타깃 백엔드. **OpenAI 호환 base_url 하나로 상업 API(키 주입)와 로컬(Ollama/vLLM/SGLang/
  LM Studio/TGI) 모두 커버**(설정만 다름). + **Manual 어댑터**(API 없는 챗봇, 사람 복붙, 멀티턴 포함).
  HTTP 클라이언트는 얇은 **openai SDK** 채택(LiteLLM 은 v0.2).
- `detectors/` — 성공 판정(judge), pluggable, 구조화 출력. MVP 3종: **RefusalMatch**(이진·휴리스틱·무모델),
  **LlamaGuard**(이진 safe/unsafe + 카테고리), **StrongREJECT**(등급 0~1, judge LLM).
- `behaviors/` — 시드 유해요청 소스(내장 팩 + jbb/harmbench 로더), `domain·subcat·tags` 메타.
- `reporting/` — 결과/지표 리포트(JSONL·터미널표·HTML).
- `core/` — 플러그인 ABC·레코드 타입·예산 wrapper·config 스키마 등 공용 기반.
- `registry.py` — 역할 패키지의 name→factory 를 aggregate. `runner.py` — 오케스트레이션. `cli.py` — `rt` 진입점.

## 설계 원칙
- **의존성 주입(DI)**: 역할 패키지는 `core` 에만 의존하고, 구체 협력자(adapter/detector)는 run 시 주입받는다.
  wiring 은 runner/registry 만 한다. → 역할 패키지가 독립 형제가 되고 fake 테스트가 쉽다.
- **Fair-ASR 예산은 wrapper 가 집계**: runner 가 타깃을 `BudgetedTarget(limit=B)` 로 감싸 주입, 세 tier 자동·균일.
- **target ≠ judge 강제**(자기 채점 금지). 비밀키는 `api_key_env`(인라인 금지), config 스냅샷은 redact.

## 레이어 계약 (import-linter 로 강제 — M14)

    cli > runner > registry > (probes | adapters | detectors | reporting | behaviors) > core

`core` 는 다른 레이어에 의존하지 않는다. openai 등 엔진 의존은 `adapters`/`detectors` 뒤로만.

## 상세
인터페이스 서명·기법 선정·judge·behaviors 시드셋은 확정되어 **`docs/plan.md`**(M0~M15)에, 로드맵은
**`docs/roadmap.md`** 에 있다.
