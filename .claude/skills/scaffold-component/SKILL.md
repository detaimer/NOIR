---
name: scaffold-component
description: redteam 의 새 역할 컴포넌트(probe/adapter/detector/reporting) 뼈대를 TDD 순서로 생성한다. 사용자가 새 공격 기법·어댑터·판정기·리포터를 추가하려 할 때 사용.
---

# scaffold-component

`redteam` 에 새 컴포넌트를 **테스트 먼저** 규율로 만든다.

## 입력
- 역할: `probe` | `adapter` | `detector` | `reporting`
- 이름: snake_case, repo 전역 유일한 basename

## 역할 → 패키지
`probe`→`src/redteam/probes/`, `adapter`→`src/redteam/adapters/`,
`detector`→`src/redteam/detectors/`, `reporting`→`src/redteam/reporting/`.

## 절차
1. `tests/test_<name>.py` 를 **먼저** 작성 — 결정론적 기대 케이스(입력→출력/판정). LLM 호출은 fake 로.
2. 해당 역할 패키지에 `<name>.py` 구현 스텁 작성 — 역할 공통 인터페이스(ABC/Protocol) 구현.
   - 인터페이스가 아직 미확정이면 `docs/architecture.md` 확인 후 인터페이스부터 확정.
3. 해당 패키지 `__init__.py` 에서 공개 심볼 재노출 (+ 레지스트리 등록).
4. `python -m pytest -q` green, `ruff check --fix` / `ruff format`.

## 주의
- basename 유일성(훅 매칭)·타입힌트·docstring 은 `references/code-style.md` / `references/testing.md` 준수.
- 커밋은 사용자 요청 시에만.
