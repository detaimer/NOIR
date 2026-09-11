# 테스트 / TDD (HOW)

작업: **모든 코드 변경**은 이 절차를 따른다. (전역 TDD 훅이 강제)

- **테스트 먼저**: `src/redteam/.../<name>.py` 를 만들기 전에 `tests/test_<name>.py` 를 먼저 작성.
- **훅 동작**: Write/Edit 로 impl `<name>.py` 를 쓰면 `test_<name>.py` 존재를 검사(PreToolUse),
  그리고 매 `.py` 쓰기 후 전체 `pytest` 를 돌려 실패 시 차단(PostToolUse).
  `__init__.py`/`conftest.py`/`test_*.py` 는 항상 허용.
- **basename 유일성**: 훅은 `test_<basename>.py` 를 basename 으로 매칭한다. 서로 다른 패키지라도
  같은 파일명(예: 두 개의 `base.py`) 금지.
- **green 유지**: 매 체크포인트에서 `python -m pytest -q` 가 통과해야 한다.
- **비결정 로직**: LLM/네트워크 호출은 Protocol/ABC 뒤에 두고 fake/mock 으로 결정론적으로 테스트.
  실제 API 호출 테스트는 marker 로 표시하고 기본 실행에서 제외.
- **레이아웃**: 테스트는 `tests/` 평면 배치. 루트 `conftest.py` 가 `src/` 를 path 에 올린다.
- **대량 파일 작업(auto 모드)**: Bash heredoc 은 훅을 우회하므로, 그럴 때도
  "테스트 먼저 + 체크포인트마다 수동 `pytest`" 규율을 지킬 것.
