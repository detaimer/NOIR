"""core.errors 도메인 예외 — raise 가능성·필드·메시지 검증."""

from __future__ import annotations

import pytest

err = pytest.importorskip("redteam.core.errors")


def test_all_inherit_base_and_exception():
    for name in ("ConfigError", "BudgetExceeded", "AdapterError", "UnknownComponent"):
        cls = getattr(err, name)
        assert issubclass(cls, err.RedteamError)
        assert issubclass(cls, Exception)


def test_config_error_raises_with_message():
    with pytest.raises(err.ConfigError) as ei:
        raise err.ConfigError("target 와 judge 가 같습니다")
    assert "target" in str(ei.value)


def test_adapter_error_raises():
    with pytest.raises(err.AdapterError):
        raise err.AdapterError("HTTP 500")


def test_budget_exceeded_carries_limit():
    e = err.BudgetExceeded(limit=50)
    assert e.limit == 50
    assert "50" in str(e)
    with pytest.raises(err.BudgetExceeded):
        raise e


def test_unknown_component_lists_available():
    e = err.UnknownComponent(role="probe", name="nope", available=("flip_attack", "pair"))
    assert e.role == "probe"
    assert e.name == "nope"
    assert e.available == ("flip_attack", "pair")
    msg = str(e)
    # 사용자에게 유효 목록을 제시해야 함
    assert "nope" in msg
    assert "flip_attack" in msg
    assert "pair" in msg
