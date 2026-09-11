# 새 공격 기법 추가 (HOW)

> ⚠️ 아직 `probes`/`adapters`/`detectors` 인터페이스(ABC)가 확정되지 않았다.
> 이 레시피는 **프로젝트 단계에서 인터페이스 확정 후** 구체화한다. 현재는 자리표시.

예정 절차 (초안):
1. `tests/test_<technique>.py` 를 **먼저** 작성 (기대 입력→변환/판정의 결정론적 케이스).
2. `src/redteam/probes/<technique>.py` 에 기법 구현 (공통 probe 인터페이스 구현).
3. `src/redteam/probes/__init__.py` 에서 재노출 + 레지스트리 등록.
4. `python -m pytest -q` green 확인, `ruff check --fix` / `ruff format` 정리.

설계 배경은 `docs/architecture.md` (모든 기법이 `{attacker?, judge?, turns, transform}` 4-필드로 환원) 참조.
