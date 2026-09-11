"""core.budget — CallCounter/BudgetedTarget (Fair-ASR 예산 자동 집계·상한)."""

from __future__ import annotations

import pytest

bud = pytest.importorskip("redteam.core.budget")
itf = pytest.importorskip("redteam.core.interfaces")
errs = pytest.importorskip("redteam.core.errors")


class _Inner:
    name = "inner"

    def __init__(self):
        self.chat_calls = 0
        self.gen_calls = 0

    def chat(self, messages):
        self.chat_calls += 1
        return "c"

    def generate(self, prompt, system=None):
        self.gen_calls += 1
        return "g"


def test_counter_starts_zero_and_increments():
    c = bud.CallCounter()
    assert c.count == 0
    c.incr()
    c.incr()
    assert c.count == 2


def test_budgeted_target_is_adapter_and_delegates():
    inner = _Inner()
    bt = bud.BudgetedTarget(inner, limit=5)
    assert isinstance(bt, itf.Adapter)
    assert bt.name == "inner"
    assert bt.generate("p") == "g"
    assert bt.chat([]) == "c"


def test_n_calls_ok_then_exceeds():
    inner = _Inner()
    counter = bud.CallCounter()
    bt = bud.BudgetedTarget(inner, limit=2, counter=counter)

    bt.generate("a")  # 1
    bt.chat([])  # 2
    assert counter.count == 2

    with pytest.raises(errs.BudgetExceeded) as ei:
        bt.generate("c")  # 3 → 초과
    assert ei.value.limit == 2
    # 초과 호출은 inner 로 전달되지 않고 카운트도 늘지 않음
    assert counter.count == 2
    assert inner.gen_calls == 1
    assert inner.chat_calls == 1


def test_shared_counter_reflects_calls_across_methods():
    inner = _Inner()
    counter = bud.CallCounter()
    bt = bud.BudgetedTarget(inner, limit=10, counter=counter)
    for _ in range(3):
        bt.generate("x")
    for _ in range(2):
        bt.chat([])
    assert counter.count == 5
