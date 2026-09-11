# 규칙: TDD (항상)

- **테스트 먼저**: impl `<name>.py` 전에 `tests/test_<name>.py` 를 작성. (전역 훅이 강제)
- **basename 유일**: 모듈 파일명은 repo 전역에서 유일하게.
- **green 유지**: 매 변경 후 `python -m pytest -q` 통과.
- **비결정 로직**은 인터페이스+mock 으로 테스트.

자세히: `references/testing.md`.
