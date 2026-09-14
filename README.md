# NOIR — NSR Opaque-box Investigation & Red-teaming

범용 **블랙박스 LLM red-teaming** 도구. 상업 API(Claude/OpenAI/Grok …)·로컬 서버(Ollama/vLLM/SGLang …)·
API 없는 챗봇(사람 중계)을 같은 계약으로 놓고, **논문 기반 공격 기법**을 적용해 취약성을 파악하고
평가한다. garak/PyRIT 류 pluggable 프레임워크를 더 세련되고 커스터마이즈 가능하게 만드는 것이 지향점.
(패키지 `redteam` · CLI `rt`)

- 프로젝트 지도: [`CLAUDE.md`](CLAUDE.md)
- 설계 / 근거: [`docs/`](docs/) — [architecture](docs/architecture.md) ·
  [evaluation](docs/evaluation.md) · [technique-fidelity](docs/technique-fidelity.md) ·
  [plan](docs/plan.md) · [roadmap](docs/roadmap.md)
- 개발 규칙: [`references/`](references/)

## 개발 셋업

    pip install -e ".[dev]"
    rt --version
    python -m pytest -q

## 실행

    rt run -c examples/run.yaml --dry-run          # 실행 계획만 확인
    rt run -c examples/run.yaml                    # 실제 실행
    rt run -c examples/run.yaml -s budget.target_calls=16 --out out/runs

설정의 원천은 **YAML run-config**([`examples/run.yaml`](examples/run.yaml))이고 `-s key=value`(dotted)
로 오버라이드한다. 산출물은 `out/runs/<ts>/` 에 `attempts.jsonl` · `summary.json` ·
`config.snapshot.yaml`(비밀키 redact) 로 남는다.

## 구성 요소

레지스트리에서 **이름으로 조회해 조합**하고 `runner` 가 오케스트레이션한다 —
`probes`(공격) × `adapters`(타깃) × `detectors`(판정).

| 역할 | 사용 가능한 이름 |
|---|---|
| **probes** | `past_tense` · `base64` · `flip_attack` · `many_shot` (정적 1-shot) · `pair` (반복형) · `crescendo` (멀티턴) |
| **adapters** | `http_openai` (OpenAI 호환 HTTP — 상업 API + 로컬 서버 공통) · `manual` (사람 중계 stdin/stdout) |
| **detectors** | `refusal_match` (무모델 이진) · `llama_guard` (safe/unsafe) · `strong_reject` (0~1 등급) · `pair_judge` (1~10) · `crescendo_refusal` · `crescendo_objective` (0~100) |

모든 기법은 `{attacker?, judge?, turns, transform}` 4-필드로 환원되어 단일 `Probe.run(behavior, ctx)`
계약으로 표현된다. 구체 협력자(adapter/detector)는 실행 시 주입되며 wiring 은 `runner`/`registry` 만 한다.

## 평가

- **detectors[0] = primary** — ASR 집계 기준. 논문식 ASR 이 필요하면 primary 를
  `pair_judge`/`crescendo_objective` 로 지정하면 코드 변경 없이 전환된다.
- **Fair-ASR** — 기법마다 쿼리 수가 다르므로(PAIR·Crescendo 는 많음) 타깃 호출을 동일 예산 `B`
  (`budget.target_calls`)로 제한해 비교한다. 예산은 `BudgetedTarget` wrapper 가 자동 집계.
- ASR 은 헤드라인 지표일 뿐 유일 축이 아니다 — 자세히는 [`docs/evaluation.md`](docs/evaluation.md).
- OT/ICS 등 도메인 특화는 하드코딩이 아니라 behavior 의 `domain` + taxonomy 태그로 표현한다.

## 기법 충실도 (fidelity)

공격 기법은 논문 기억으로 재현하지 않는다. **원저자 프롬프트는 byte-verbatim vendor + 루프는 원본
코드를 보고 충실히 재구현 + 출처·라이선스 기록**이 정책이며, 상위 패키지를 import/pip-의존하지 않는다.
vendored 자산은 `src/redteam/vendor/<technique>/` 에 원본 `LICENSE` 와 `PROVENANCE.md`
(repo·commit SHA·원본 경로·파일별 sha256·DEVIATIONS)를 동반한다.

- 정책과 근거: [`docs/technique-fidelity.md`](docs/technique-fidelity.md)
- 추가 절차: [`references/adding-a-technique.md`](references/adding-a-technique.md)
- 서드파티 고지: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## 개발 규칙

**TDD 강제** — `<name>.py` 보다 `tests/test_<name>.py` 를 먼저 쓰고(전역 훅이 검사), 모듈 basename 은
repo 전역에서 유일하게, 매 변경 후 `python -m pytest -q` 를 green 으로 유지한다.
자세히는 [`references/testing.md`](references/testing.md) · [`references/code-style.md`](references/code-style.md) ·
[`references/git-workflow.md`](references/git-workflow.md).
