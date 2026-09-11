"""Crescendo probe — 멀티턴 escalation: 대화 성장·턴별 judge·성공/max_turns 중단 (DI 컨텍스트)."""

from __future__ import annotations

import random

import pytest

pytest.importorskip("redteam.probes.crescendo_probe")

from redteam.core import (  # noqa: E402
    AdapterError,
    Behavior,
    BudgetedTarget,
    CallCounter,
    DetectionResult,
    Detector,
    ProbeContext,
    Role,
)
from redteam.probes.crescendo_probe import CrescendoProbe  # noqa: E402


def _behavior() -> Behavior:
    return Behavior(id="b1", prompt="original objective", domain="cyber")


def _ctx(target_inner, judge, attacker, *, max_turns, limit):
    """BudgetedTarget 로 감싼 ProbeContext 를 만들고 (ctx, counter) 를 돌려준다."""
    counter = CallCounter()
    budgeted = BudgetedTarget(target_inner, limit, counter)
    ctx = ProbeContext(
        target=budgeted,
        judge=judge,
        attacker=attacker,
        max_turns=max_turns,
        max_attempts=limit,
        rng=random.Random(0),
    )
    return ctx, counter


class RecordingJudge(Detector):
    """judge 호출 때 받은 conversation 길이를 기록하는 테스트용 Detector(항상 실패)."""

    name = "recording"

    def __init__(self) -> None:
        self.conversation_lengths: list[int] = []

    def judge(self, behavior, prompt, response, conversation=None) -> DetectionResult:
        self.conversation_lengths.append(len(conversation) if conversation is not None else 0)
        return DetectionResult(success=False, judge_name=self.name)


def test_crescendo_attrs() -> None:
    probe = CrescendoProbe()
    assert probe.name == "crescendo"
    assert probe.uses_attacker is True
    assert probe.uses_judge is True
    assert probe.default_turns == 5


def test_crescendo_conversation_grows(fake_adapter, fake_judge) -> None:
    inner = fake_adapter(["a1", "a2", "a3"])
    attacker = fake_adapter(["u1", "u2", "u3"])
    ctx, _ = _ctx(inner, fake_judge(success=False), attacker, max_turns=3, limit=10)

    CrescendoProbe().run(_behavior(), ctx)

    assert len(inner.calls) == 3
    for i, call in enumerate(inner.calls):
        kind, messages = call
        assert kind == "chat"
        # 매 턴 대화가 전량 전송되며 (user, assistant) 가 누적 → 길이 1,3,5
        assert len(messages) == 2 * i + 1
        # 마지막 메시지는 이번 턴의 새 user 발화
        assert messages[-1].role == Role.USER
        assert messages[-1].content == f"u{i + 1}"
        # 역할 교대 확인
        for j, m in enumerate(messages):
            assert m.role == (Role.USER if j % 2 == 0 else Role.ASSISTANT)


def test_crescendo_stops_on_success(fake_adapter, fake_judge) -> None:
    inner = fake_adapter(["a1", "a2", "a3"])
    attacker = fake_adapter(["u1", "u2", "u3"])
    judge = fake_judge(success_on_call=2)
    ctx, counter = _ctx(inner, judge, attacker, max_turns=5, limit=10)

    attempt = CrescendoProbe().run(_behavior(), ctx)

    assert attempt.success is True
    assert attempt.target_calls == 2
    assert attempt.attacker_calls == 2
    assert attempt.judge_calls == 2
    assert len(attempt.turns) == 2
    assert attempt.final_response == "a2"
    assert counter.count == 2
    assert len(inner.calls) == 2


def test_crescendo_stops_at_max_turns(fake_adapter, fake_judge) -> None:
    inner = fake_adapter(["a1", "a2", "a3", "a4"])
    attacker = fake_adapter(["u1", "u2", "u3", "u4"])
    ctx, _ = _ctx(inner, fake_judge(success=False), attacker, max_turns=3, limit=10)

    attempt = CrescendoProbe().run(_behavior(), ctx)

    assert attempt.target_calls == 3
    assert attempt.attacker_calls == 3
    assert attempt.judge_calls == 3
    assert attempt.success is False


def test_crescendo_judge_receives_conversation(fake_adapter) -> None:
    inner = fake_adapter(["a1", "a2"])
    attacker = fake_adapter(["u1", "u2"])
    judge = RecordingJudge()
    ctx, _ = _ctx(inner, judge, attacker, max_turns=2, limit=10)

    CrescendoProbe().run(_behavior(), ctx)

    # 턴마다 성장하는 Turn 리스트가 judge 에 전달된다.
    assert judge.conversation_lengths == [1, 2]


def test_crescendo_attacker_sees_conversation_context(fake_adapter, fake_judge) -> None:
    inner = fake_adapter(["a1", "a2"])
    attacker = fake_adapter(["u1", "u2"])
    ctx, _ = _ctx(inner, fake_judge(success=False), attacker, max_turns=2, limit=10)

    CrescendoProbe().run(_behavior(), ctx)

    first_prompt = attacker.calls[0][1]
    second_prompt = attacker.calls[1][1]
    # 첫 턴은 objective 만, 두 번째 턴은 직전 user/assistant transcript 가 실려야 함.
    assert "original objective" in first_prompt
    assert "u1" in second_prompt
    assert "a1" in second_prompt


def test_crescendo_budget_exceeded_propagates(fake_adapter, fake_judge) -> None:
    from redteam.core import BudgetExceeded

    inner = fake_adapter(["a1", "a2", "a3", "a4", "a5"])
    attacker = fake_adapter(["u1", "u2", "u3", "u4", "u5"])
    ctx, counter = _ctx(inner, fake_judge(success=False), attacker, max_turns=5, limit=2)

    # max_turns(5) 가 budget(2) 과 독립 → 3번째 chat 에서 BudgetExceeded 전파.
    with pytest.raises(BudgetExceeded):
        CrescendoProbe().run(_behavior(), ctx)
    assert counter.count == 2


def test_crescendo_requires_attacker(fake_adapter, fake_judge) -> None:
    inner = fake_adapter(["a1"])
    ctx, _ = _ctx(inner, fake_judge(success=True), None, max_turns=3, limit=10)

    with pytest.raises(AdapterError):
        CrescendoProbe().run(_behavior(), ctx)
