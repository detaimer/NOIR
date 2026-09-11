"""Fair-ASR 예산 — CallCounter 와 BudgetedTarget wrapper.

runner 가 실제 타깃을 `BudgetedTarget(limit=B)` 로 감싸 probe 에 주입하면, 매 chat/generate 가
자동 집계되고 상한 초과 시 BudgetExceeded 를 던진다. probe 는 예산을 자가보고하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass

from redteam.core.errors import BudgetExceeded
from redteam.core.records import Message


@dataclass
class CallCounter:
    """타깃 호출 누적 카운터 (Attempt.target_calls 로 기록됨)."""

    count: int = 0

    def incr(self) -> None:
        self.count += 1


class BudgetedTarget:
    """Adapter 를 감싸 호출 수를 집계하고 예산 상한을 강제하는 wrapper.

    limit 회까지 허용, 그 다음 호출부터 BudgetExceeded. 초과 호출은 inner 로 전달되지 않는다.
    """

    def __init__(self, inner: object, limit: int, counter: CallCounter | None = None) -> None:
        self._inner = inner
        self._limit = limit
        self.counter = counter if counter is not None else CallCounter()
        self.name = getattr(inner, "name", "target")

    def _charge(self) -> None:
        if self.counter.count >= self._limit:
            raise BudgetExceeded(self._limit)
        self.counter.incr()

    def chat(self, messages: list[Message]) -> str:
        self._charge()
        return self._inner.chat(messages)

    def generate(self, prompt: str, system: str | None = None) -> str:
        self._charge()
        return self._inner.generate(prompt, system)
