"""PAIR probe — 반복형 단일턴 정제: attacker 제안 → target → judge → 피드백 재작성 (DI 컨텍스트)."""

from __future__ import annotations

import random

import pytest

pytest.importorskip("redteam.probes.pair_probe")

from redteam.core import (  # noqa: E402
    AdapterError,
    Behavior,
    BudgetedTarget,
    CallCounter,
    ProbeContext,
)
from redteam.probes.pair_probe import PairProbe  # noqa: E402


def _behavior() -> Behavior:
    return Behavior(id="b1", prompt="original request", domain="cyber")


def _ctx(target_inner, judge, attacker, *, max_attempts, limit):
    """BudgetedTarget 로 감싼 ProbeContext 를 만들고 (ctx, counter) 를 돌려준다."""
    counter = CallCounter()
    budgeted = BudgetedTarget(target_inner, limit, counter)
    ctx = ProbeContext(
        target=budgeted,
        judge=judge,
        attacker=attacker,
        max_turns=1,
        max_attempts=max_attempts,
        rng=random.Random(0),
    )
    return ctx, counter


def test_pair_probe_attrs() -> None:
    probe = PairProbe()
    assert probe.name == "pair"
    assert probe.uses_attacker is True
    assert probe.uses_judge is True
    assert probe.default_turns == 1


def test_pair_stops_on_success_k(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(["adv1", "adv2", "adv3"])
    judge = fake_judge(success_on_call=2)  # 2번째 judge 호출부터 성공
    ctx, counter = _ctx(inner, judge, attacker, max_attempts=5, limit=5)

    attempt = PairProbe().run(_behavior(), ctx)

    assert attempt.success is True
    assert attempt.target_calls == 2
    assert attempt.attacker_calls == 2
    assert attempt.judge_calls == 2
    assert len(attempt.turns) == 2
    assert attempt.final_prompt == "adv2"
    assert attempt.final_response == "resp"
    assert counter.count == 2
    assert len(inner.calls) == 2
    assert len(attacker.calls) == 2


def test_pair_target_receives_attacker_prompt(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(["adv1", "adv2"])
    ctx, _ = _ctx(inner, fake_judge(success=True), attacker, max_attempts=5, limit=5)

    PairProbe().run(_behavior(), ctx)

    # target 은 attacker 가 제안한 공격 프롬프트를 그대로(변환 없이) 받는다.
    assert inner.calls[0] == ("generate", "adv1", None)


def test_pair_feeds_judge_feedback_into_refinement(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp-text")
    attacker = fake_adapter(["adv1", "adv2"])
    judge = fake_judge(success_on_call=2, score=0.3)
    ctx, _ = _ctx(inner, judge, attacker, max_attempts=5, limit=5)

    PairProbe().run(_behavior(), ctx)

    first_prompt = attacker.calls[0][1]
    second_prompt = attacker.calls[1][1]
    # 첫 라운드엔 피드백 없음, 두 번째엔 직전 공격/응답/점수가 실려야 함.
    assert "adv1" not in first_prompt
    assert "adv1" in second_prompt
    assert "resp-text" in second_prompt
    assert "0.3" in second_prompt


def test_pair_exhausts_max_attempts_without_success(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(["a1", "a2", "a3", "a4"])
    ctx, _ = _ctx(inner, fake_judge(success=False), attacker, max_attempts=3, limit=10)

    attempt = PairProbe().run(_behavior(), ctx)

    # 루프는 budget 이 아니라 max_attempts 로 한정된다.
    assert attempt.target_calls == 3
    assert attempt.attacker_calls == 3
    assert attempt.judge_calls == 3
    assert attempt.success is False
    assert len(attempt.turns) == 3


def test_pair_budget_exceeded_propagates(fake_adapter, fake_judge) -> None:
    from redteam.core import BudgetExceeded

    inner = fake_adapter("resp")
    attacker = fake_adapter(["a1", "a2", "a3", "a4", "a5"])
    ctx, counter = _ctx(inner, fake_judge(success=False), attacker, max_attempts=5, limit=2)

    # budget(2) < max_attempts(5): 3번째 호출에서 BudgetExceeded 전파(probe 가 삼키지 않음).
    with pytest.raises(BudgetExceeded):
        PairProbe().run(_behavior(), ctx)
    assert counter.count == 2


def test_pair_binary_judge_graceful(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(["adv1", "adv2"])
    judge = fake_judge(success_on_call=2, score=None)  # 이진 judge (점수 없음)
    ctx, _ = _ctx(inner, judge, attacker, max_attempts=5, limit=5)

    attempt = PairProbe().run(_behavior(), ctx)

    assert attempt.success is True
    assert attempt.target_calls == 2
    # 점수가 없어도 크래시 없이 피드백에 N/A 로 렌더된다.
    assert "N/A" in attacker.calls[1][1]


def test_pair_requires_attacker(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    ctx, _ = _ctx(inner, fake_judge(success=True), None, max_attempts=5, limit=5)

    with pytest.raises(AdapterError):
        PairProbe().run(_behavior(), ctx)
