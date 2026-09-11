# 코드 스타일 (HOW)

작업: **코드를 작성/수정할 때** 이 문서를 따른다.

- **포맷/린트**: `ruff format` + `ruff check`. line-length 100. import 정렬은 ruff(I).
- **타입힌트 필수**: 모든 공개 함수/메서드 시그니처에 타입. `from __future__ import annotations` 사용.
- **docstring**: 공개 모듈/클래스/함수에 한 줄 요약 이상(한국어 OK).
- **순수성**: 로직은 순수함수로, 부작용(네트워크·파일·랜덤)은 경계(`adapters`·io)로 격리.
- **비결정 요소**: LLM 호출 등은 인터페이스(Protocol/ABC) 뒤에 두고, 테스트는 결정론적 mock 으로.
- **에러 처리**: 광범위 `except:` 금지. 도메인 예외는 `core` 에 정의.
- **네이밍**: 모듈 basename 은 repo 전역 **유일**(TDD 훅이 basename 으로 test 매칭). 자세히는 `testing.md`.
- **공개 API**: 역할 패키지는 `__init__.py` 에서 공개 심볼을 재노출해 `from redteam.probes import X` 가 안정적이게.
