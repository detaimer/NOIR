# NOIR — NSR Opaque-box Investigation & Red-teaming

**LLM(챗봇 AI)이 얼마나 쉽게 뚫리는지 자동으로 시험해 보는 도구**입니다.
논문에 나온 여러 "탈옥(jailbreak)" 공격 기법을 골라, 시험할 모델에 실제로 던져 보고,
그 모델이 위험한 요청에 넘어갔는지를 판정해 점수로 정리해 줍니다.

시험 대상은 세 가지를 똑같은 방식으로 다룹니다:
- **상업 API** — Claude, OpenAI, Grok 등
- **로컬 서버** — Ollama, vLLM, SGLang 등으로 직접 띄운 모델
- **API 없는 챗봇** — 사람이 직접 복붙해서 응답을 중계

garak·PyRIT 같은 기존 도구를 더 깔끔하고 바꿔 끼우기 쉽게 만드는 게 목표입니다.
(파이썬 패키지 이름은 `redteam`, 터미널 명령은 `rt`)

**지금 상태**: 기본 기능(v0.2)은 다 만들어졌습니다. 다음 할 일은 v0.3 — "**나오는 점수를 믿을 수 있게 만들기**"
입니다(실제 모델로 시험해 보니 기본 판정기가 무해한 답변도 "뚫림"으로 잘못 세는 문제가 있었음).
자세한 계획: [`docs/plan-v0.3.md`](docs/plan-v0.3.md) · 전체 그림: [`docs/roadmap.md`](docs/roadmap.md)

## 설치하고 확인하기

    pip install -e ".[dev]"     # 설치
    rt --version                # 잘 깔렸는지 확인
    python -m pytest -q         # 테스트가 다 통과하는지 확인

## 실행하기

    rt run -c examples/run.yaml --dry-run      # 실제로 안 돌리고 "무엇을 할지"만 미리 보기
    rt run -c examples/run.yaml                # 진짜 실행
    rt run -c examples/run.yaml -s budget.target_calls=16    # 값 하나 바꿔서 실행

어떻게 시험할지는 **YAML 설정 파일** 하나에 적습니다(예제: [`examples/run.yaml`](examples/run.yaml)).
파일을 안 고치고 그때그때 바꾸고 싶으면 `-s 항목=값` 으로 덮어씁니다.

실행이 끝나면 결과가 `out/runs/<시각>/` 폴더에 저장됩니다:
- `attempts.jsonl` — 시도별 기록(무슨 프롬프트를 보내고 어떤 답이 왔는지)
- `summary.json` — 점수 요약
- `config.snapshot.yaml` — 이번에 쓴 설정 사본(API 키는 가려서 저장)
- `report.html` — 브라우저로 열어 보는 리포트(위험도 히트맵·대화 내용 보기)
- 그리고 터미널에 요약표가 바로 출력됩니다.

## 무엇으로 이루어져 있나

세 종류의 부품을 **이름으로 골라 조합**하고, `runner` 가 순서대로 실행합니다.

| 부품 | 하는 일 | 고를 수 있는 이름 |
|---|---|---|
| **probes** | 공격 기법 | `past_tense` · `base64` · `flip_attack` · `many_shot` (한 번에 끝나는 기법) · `pair` (반복하며 다듬는 기법) · `crescendo` (여러 턴에 걸쳐 서서히) |
| **adapters** | 시험할 모델에 연결 | `http_openai` (상업 API·로컬 서버 공통) · `manual` (사람이 직접 중계) |
| **detectors** | 답변이 "뚫린 것"인지 판정 | `refusal_match` (거절 문구만 보는 무모델 방식) · `llama_guard` (안전/위험) · `strong_reject` (0~1 점수) · `pair_judge` (1~10) · `crescendo_refusal` · `crescendo_objective` (0~1) |

새 공격 기법을 넣어도 나머지 코드는 안 건드리게 설계돼 있습니다(부품은 실행할 때 끼워 넣음).

## 점수는 어떻게 읽나

- **ASR(공격 성공률)** = 성공한 시도 ÷ 전체 시도. 가장 대표적인 숫자입니다.
- 판정기(detector)는 여러 개 붙일 수 있고, **맨 앞에 놓은 것이 대표 점수를 정합니다.**
- ⚠️ 기본 판정기 `refusal_match` 는 "모델이 거절만 안 하면 성공"으로 세기 때문에,
  **무해한 답변도 성공으로 잘못 잡는 경우가 많습니다**(실제 모델로 확인함). 그래서 답변이 진짜
  위험한지 보는 판정기(`llama_guard` 등)를 앞에 두길 권합니다. 이걸 기본값으로 바꾸는 건 v0.3 작업.
- **Fair-ASR** — `pair`·`crescendo` 는 한 번에 모델을 여러 번 부르기 때문에 그냥 비교하면 불공평합니다.
  그래서 **모델을 부를 수 있는 횟수(예산 `B`)를 똑같이 맞춰** 놓고 비교합니다.
- ASR 이 전부는 아닙니다. 더 자세히는 [`docs/evaluation.md`](docs/evaluation.md).
- 정수장 제어시스템(OT/ICS) 같은 특수 분야는 코드로 특별 취급하지 않고, 요청에 붙인 태그로 표현합니다.

## 공격 기법은 원본 그대로 (fidelity)

공격 기법을 기억에 의존해 대충 재현하지 않습니다. **원저자가 쓴 프롬프트는 글자 그대로 복사해 보관하고,
동작은 원본 코드를 보며 충실히 다시 구현하며, 출처와 라이선스를 함께 남깁니다.** 남의 패키지를
그대로 import 하지도 않습니다. 복사한 자료는 `src/redteam/vendor/<기법>/` 아래에 원본 `LICENSE` 와
출처 기록(`PROVENANCE.md`)과 함께 둡니다.

- 정책과 이유: [`docs/technique-fidelity.md`](docs/technique-fidelity.md)
- 기법 추가 방법: [`references/adding-a-technique.md`](references/adding-a-technique.md)
- 외부 자료 고지: [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)

## 개발 규칙

**테스트 먼저(TDD)** — 코드 `<name>.py` 를 쓰기 전에 테스트 `tests/test_<name>.py` 를 먼저 만듭니다
(전역 훅이 검사). 파일 이름은 겹치지 않게, 변경할 때마다 `python -m pytest -q` 가 통과하도록 유지합니다.
자세히: [`references/testing.md`](references/testing.md) · [`references/code-style.md`](references/code-style.md) ·
[`references/git-workflow.md`](references/git-workflow.md)

## 더 읽을거리

- 프로젝트 전체 지도: [`CLAUDE.md`](CLAUDE.md)
- 설계·근거 문서: [`docs/`](docs/) — [architecture](docs/architecture.md) · [evaluation](docs/evaluation.md) ·
  [technique-fidelity](docs/technique-fidelity.md) · [plan (v0.2)](docs/plan.md) ·
  [plan-v0.3](docs/plan-v0.3.md) · [roadmap](docs/roadmap.md)
- 개발 규칙 모음: [`references/`](references/)
