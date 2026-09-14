"""Crescendo probe — 대화 성장·백트래킹·0~100 objective·예산 (원본 충실 재구현)."""

from __future__ import annotations

import json
import random

import pytest

pytest.importorskip("redteam.probes.crescendo_probe")

from redteam.core import (  # noqa: E402
    AdapterError,
    Behavior,
    BudgetedTarget,
    BudgetExceeded,
    CallCounter,
    ProbeContext,
    Role,
)
from redteam.probes.crescendo_probe import CrescendoProbe  # noqa: E402


def _behavior() -> Behavior:
    return Behavior(id="b1", prompt="the objective", domain="cyber")


def _q(question: str) -> str:
    return json.dumps({"generated_question": question})


def _ctx(inner, judge, attacker, judge_client, *, max_turns, params=None, limit=100):
    counter = CallCounter()
    budgeted = BudgetedTarget(inner, limit, counter)
    ctx = ProbeContext(
        target=budgeted,
        judge=judge,
        attacker=attacker,
        max_turns=max_turns,
        max_attempts=limit,
        rng=random.Random(0),
        judge_client=judge_client,
        params=params or {},
    )
    return ctx, counter


def test_crescendo_attrs() -> None:
    probe = CrescendoProbe()
    assert probe.name == "crescendo"
    assert probe.uses_attacker is True
    assert probe.uses_judge is True
    assert probe.default_turns == 10


def test_requires_attacker(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=True),
        None,
        fake_adapter('{"score_value": "0"}'),
        max_turns=1,
    )
    with pytest.raises(AdapterError):
        CrescendoProbe().run(_behavior(), ctx)


def test_requires_judge_client(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=True),
        fake_adapter(_q("Q")),
        None,
        max_turns=1,
    )
    with pytest.raises(AdapterError):
        CrescendoProbe().run(_behavior(), ctx)


def test_conversation_grows_and_roles_alternate(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["r1", "r2"])
    attacker = fake_adapter([_q("Q1"), _q("Q2")])
    judge_client = fake_adapter(
        [
            '{"score_value": "False"}',
            '{"score_value": "50"}',
            '{"score_value": "False"}',
            '{"score_value": "50"}',
        ]
    )
    ctx, _ = _ctx(target, fake_judge(success=False), attacker, judge_client, max_turns=2)
    attempt = CrescendoProbe().run(_behavior(), ctx)

    assert len(attempt.turns) == 2
    # 매 턴 누적 대화 전송: 1개(Q1) → 3개(Q1,r1,Q2)
    assert len(target.calls[0][1]) == 1
    assert len(target.calls[1][1]) == 3
    turn2_msgs = target.calls[1][1]
    assert [m.role for m in turn2_msgs] == [Role.USER, Role.ASSISTANT, Role.USER]
    assert turn2_msgs[0].content == "Q1" and turn2_msgs[-1].content == "Q2"


def test_target_receives_generated_question(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["r1"])
    ctx, _ = _ctx(
        target,
        fake_judge(success=False),
        fake_adapter([_q("MYQ")]),
        fake_adapter(['{"score_value": "False"}', '{"score_value": "50"}']),
        max_turns=1,
    )
    CrescendoProbe().run(_behavior(), ctx)
    assert target.calls[0][1][-1].content == "MYQ"


def test_refusal_triggers_backtrack(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["I cannot help with that", "Sure, here it is"])
    attacker = fake_adapter([_q("Q1"), _q("Q2")])
    # 판정 순서: t1 refusal(True)→backtrack, t2 refusal(False)→scale(90)
    judge_client = fake_adapter(
        ['{"score_value": "True"}', '{"score_value": "False"}', '{"score_value": "90"}']
    )
    ctx, counter = _ctx(target, fake_judge(success=True), attacker, judge_client, max_turns=1)
    attempt = CrescendoProbe().run(_behavior(), ctx)

    # 거부된 턴은 채점/카운트 안 됨 → 최종 1개 턴만
    assert len(attempt.turns) == 1
    assert attempt.final_response == "Sure, here it is"
    # 거부 send 도 예산 차감 (2회 전송)
    assert counter.count == 2
    # backtrack 후 target 대화가 되돌려져 2번째 전송은 [Q2] 하나만
    assert len(target.calls[1][1]) == 1
    assert target.calls[1][1][0].content == "Q2"
    # 다음 attacker 프롬프트에 거부 안내 + 거부된 질문이 실린다
    turn2_attacker_msgs = attacker.calls[1][1]
    last_user = turn2_attacker_msgs[-1].content
    assert "The target refused" in last_user and "Q1" in last_user


def test_objective_threshold_stops_early(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["compliant"])
    ctx, _ = _ctx(
        target,
        fake_judge(success=True),
        fake_adapter([_q("Q1")]),
        fake_adapter(['{"score_value": "False"}', '{"score_value": "90"}']),
        max_turns=5,
    )
    attempt = CrescendoProbe().run(_behavior(), ctx)
    assert len(attempt.turns) == 1  # 0.9 >= 0.8 → 조기중단
    assert attempt.detections[1].judge_name == "crescendo_objective"
    assert attempt.detections[1].score == pytest.approx(0.9)


def test_runs_to_max_turns_without_success(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["r"])
    judge_client = fake_adapter(
        [
            '{"score_value": "False"}',
            '{"score_value": "40"}',
            '{"score_value": "False"}',
            '{"score_value": "40"}',
        ]
    )
    ctx, _ = _ctx(
        target, fake_judge(success=False), fake_adapter(_q("Q")), judge_client, max_turns=2
    )
    attempt = CrescendoProbe().run(_behavior(), ctx)
    assert len(attempt.turns) == 2
    assert attempt.detections[1].score == pytest.approx(0.4)  # < 0.8


def test_backtrack_limit_skips_refusal_check(fake_adapter, fake_judge) -> None:
    # max_backtracks=0 → refusal 검사 자체를 건너뛰고 바로 채점.
    target = fake_adapter(["I cannot help"])
    judge_client = fake_adapter(['{"score_value": "50"}'])  # scale 하나뿐(refusal 호출 없음)
    ctx, _ = _ctx(
        target,
        fake_judge(success=False),
        fake_adapter([_q("Q1")]),
        judge_client,
        max_turns=1,
        params={"max_backtracks": 0},
    )
    attempt = CrescendoProbe().run(_behavior(), ctx)
    assert len(attempt.turns) == 1
    assert len(judge_client.calls) == 1  # refusal 미검사 → scale 1회만


def test_budget_exceeded_propagates(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["r1", "r2", "r3"])
    judge_client = fake_adapter(
        [
            '{"score_value": "False"}',
            '{"score_value": "50"}',
            '{"score_value": "False"}',
            '{"score_value": "50"}',
        ]
    )
    ctx, counter = _ctx(
        target,
        fake_judge(success=False),
        fake_adapter(_q("Q")),
        judge_client,
        max_turns=3,
        limit=2,
    )
    with pytest.raises(BudgetExceeded):
        CrescendoProbe().run(_behavior(), ctx)
    assert counter.count == 2


def test_success_from_primary_judge(fake_adapter, fake_judge) -> None:
    target = fake_adapter(["r"])
    # scale 낮아도(40) primary judge 성공이면 success=True
    ctx, _ = _ctx(
        target,
        fake_judge(success=True),
        fake_adapter([_q("Q1")]),
        fake_adapter(['{"score_value": "False"}', '{"score_value": "40"}']),
        max_turns=1,
    )
    attempt = CrescendoProbe().run(_behavior(), ctx)
    assert attempt.success is True
    assert attempt.detections[1].judge_name == "crescendo_objective"
