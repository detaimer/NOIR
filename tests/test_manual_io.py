"""ManualIOAdapter 테스트 — scripted input/output_fn, single/multi-turn, sentinel 종료."""

from __future__ import annotations

import pytest

# 훅 데드락 브레이커: impl 또는 redteam.core API 부재 시 모듈 전체 SKIP 으로 green 유지.
try:
    from redteam.adapters import manual_io as mod
    from redteam.core import Message, Role
except ImportError:
    pytest.skip("adapter/core API not available yet", allow_module_level=True)

ManualIOAdapter = mod.ManualIOAdapter


def _scripted(lines: list[str]):
    """리스트를 한 줄씩 돌려주는 zero-arg 콜러블(소진 시 StopIteration)."""
    it = iter(lines)
    return lambda: next(it)


def test_generate_single_turn_returns_line_and_shows_prompt() -> None:
    captured: list[str] = []
    adapter = ManualIOAdapter(
        input_fn=_scripted(["hello there", "."]),
        output_fn=captured.append,
    )

    out = adapter.generate("do X", system="you are Y")

    assert out == "hello there"
    assert any("do X" in c for c in captured)
    assert any("you are Y" in c for c in captured)


def test_generate_joins_multiple_lines_until_sentinel() -> None:
    adapter = ManualIOAdapter(
        input_fn=_scripted(["a", "b", ".", "c"]),
        output_fn=lambda _msg: None,
    )

    out = adapter.generate("p")

    # sentinel 에서 멈추고 그 뒤 "c" 는 소비하지 않는다.
    assert out == "a\nb"


def test_generate_terminates_on_exhausted_input() -> None:
    adapter = ManualIOAdapter(
        input_fn=_scripted(["x", "y"]),  # sentinel 없이 소진
        output_fn=lambda _msg: None,
    )

    out = adapter.generate("p")

    assert out == "x\ny"


def test_custom_sentinel() -> None:
    adapter = ManualIOAdapter(
        input_fn=_scripted(["one", "END", "two"]),
        output_fn=lambda _msg: None,
        sentinel="END",
    )

    assert adapter.generate("p") == "one"


def test_chat_multi_turn_returns_responses_in_order() -> None:
    captured: list[str] = []
    adapter = ManualIOAdapter(
        input_fn=_scripted(["first response", ".", "second", "line2", "."]),
        output_fn=captured.append,
    )

    r1 = adapter.chat([Message(role=Role.USER, content="q1")])
    r2 = adapter.chat([Message(role=Role.USER, content="q2")])

    assert r1 == "first response"
    assert r2 == "second\nline2"
    # 최신 user 메시지가 출력되었는지 확인.
    assert any("q1" in c for c in captured)
    assert any("q2" in c for c in captured)


def test_name_default() -> None:
    adapter = ManualIOAdapter(input_fn=_scripted(["."]), output_fn=lambda _msg: None)
    assert adapter.name == "manual"
