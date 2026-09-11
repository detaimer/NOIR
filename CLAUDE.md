# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# redteam (`rt`)

범용 **블랙박스 LLM red-teaming** MVP. 타깃 모델(상업 API — Claude/OpenAI/Grok 등, 또는 로컬 서버 —
Ollama/vLLM/SGLang 등으로 구동하는 DeepSeek 등, 또는 API 없는 챗봇을 사람이 중계하는 Manual)에 논문 기반
공격 기법을 적용해 취약성을 파악하고 평가한다. **garak/PyRIT 류의 pluggable 프레임워크 — 더 세련되고
커스터마이즈 가능하게** 가 지향점. ASR은 기본 헤드라인 지표일 뿐 유일 축이 아니다(아래 참조).

## 지도

- `src/redteam/` — 모든 로직 (역할별 서브패키지)
  - `probes/` 공격 기법 · `adapters/` 타깃 백엔드 · `detectors/` 성공 판정(judge)
  - `reporting/` 결과·지표 리포트 · `core/` 공용 기반(ABC·레코드·레지스트리용 타입)
  - `cli.py` 진입점(`rt`). *계획*: `runner.py`·`registry.py`·`behaviors/` 추가 (→ `docs/plan.md`)
- `tests/` — 검증 인프라 (모듈당 `test_<name>.py`, 평면 배치)
- `references/` — 작업 중 참조하는 운영 규칙 (HOW, 온디맨드) · `docs/` — 설계·근거 (WHY)
- `out/` — 실행 산출물 (gitignored; `out/runs/<ts>/`)

## 개발 명령

```bash
pip install -e ".[dev]"                 # 설치 (editable). 파일 이동/패키지 추가 후 재실행
python -m pytest -q                      # 전체 테스트 (루트 conftest.py 가 src/ 를 path 에 올림)
python -m pytest tests/test_<name>.py    # 단일 파일
python -m pytest -k <expr>               # 이름 패턴으로 선택 / tests/test_x.py::test_fn 로 단일 테스트
ruff check . && ruff format .            # 린트·포맷 (line-length 100)
rt --version   /   rt --help             # CLI (계획 후: rt run -c run.yaml)
```
*계획 반영 후 추가*: 실 엔드포인트 테스트는 `@pytest.mark.live` 로 기본 제외(`pytest -m live` 로만 실행),
레이어·의존성 검사는 `lint-imports` 와 `deptry src`.

## 아키텍처 한눈에 (big picture — 자세히는 `docs/plan.md`, `docs/architecture.md`)

- **조합 구조**: `probes`(공격)·`adapters`(타깃)·`detectors`(judge) 를 레지스트리로 이름 조회해 조합하고,
  `runner` 가 오케스트레이션한다. 설정은 **YAML run-config**(원천) + CLI 오버라이드.
- **모든 기법은 `{attacker?, judge?, turns, transform}` 4-필드로 환원** → 단일 `Probe.run(behavior, ctx)`
  계약으로 정적(one-shot)·PAIR(반복)·Crescendo(멀티턴)를 전부 표현.
- **DI 원칙**: 역할 패키지는 `core` 에만 의존하고 구체 협력자(adapter/detector)는 **run 시 주입**받는다.
  wiring 은 `runner`/`registry` 만 한다. 레이어 계약(import-linter 로 강제 예정):
  `cli > runner > registry > (probes | adapters | detectors | reporting | behaviors) > core`.
- **타깃 어댑터**: OpenAI 호환 HTTP 하나로 상업 API + 로컬 서버 커버(차이는 base_url/key/model 설정뿐),
  그리고 Manual 어댑터. **judge(detector)** 는 pluggable, 구조화 출력 `{success, score?, categories}` —
  RefusalMatch(이진·무모델)·LlamaGuard(이진 safe/unsafe)·StrongREJECT(등급 0~1). `reporting` 이 ASR·평균
  점수·카테고리/도메인/taxonomy별로 집계한다.
- **Fair-ASR**: 기법마다 쿼리 수가 달라(PAIR·Crescendo는 많음) 타깃 호출을 동일 예산 B 로 제한해 비교.
  예산은 `core` 의 `BudgetedTarget` wrapper 가 자동 집계.
- **OT/ICS** 등 도메인 특화는 하드코딩이 아니라 behavior 의 `domain`+taxonomy 태그로 표현된다.

## 작업별 참조

- 코드 작성 → `references/code-style.md`
- 테스트 / TDD → `references/testing.md`
- 커밋 / 브랜치 → `references/git-workflow.md`
- 새 공격 기법 추가 → `references/adding-a-technique.md`
- 설계 이해 → `docs/architecture.md`, `docs/evaluation.md`, `docs/roadmap.md`
- **기능 구현 계획(전 task·인터페이스) → `docs/plan.md`**

## 항상 지켜야 할 규칙

@.claude/rules/tdd.md
