"""PAIR probe — 원본 충실 재구현 검증: 다중 스트림·3전략·JSON 파싱·1~10 judge·keep_last_n·예산."""

from __future__ import annotations

import json
import random

import pytest

pytest.importorskip("redteam.probes.pair_probe")

from redteam.core import (  # noqa: E402
    AdapterError,
    Behavior,
    BudgetedTarget,
    BudgetExceeded,
    CallCounter,
    ConfigError,
    ProbeContext,
)
from redteam.probes.pair_probe import PairProbe  # noqa: E402


def _behavior() -> Behavior:
    return Behavior(id="b1", prompt="original request", domain="cyber")


def _json(prompt: str, improvement: str = "i") -> str:
    return json.dumps({"improvement": improvement, "prompt": prompt})


def _ctx(inner, judge, attacker, judge_client, *, params, limit=100):
    counter = CallCounter()
    budgeted = BudgetedTarget(inner, limit, counter)
    ctx = ProbeContext(
        target=budgeted,
        judge=judge,
        attacker=attacker,
        max_turns=1,
        max_attempts=limit,
        rng=random.Random(0),
        judge_client=judge_client,
        params=params,
    )
    return ctx, counter


def test_pair_probe_attrs() -> None:
    probe = PairProbe()
    assert probe.name == "pair"
    assert probe.uses_attacker is True
    assert probe.uses_judge is True
    assert probe.default_turns == 1


def test_requires_attacker(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=True),
        None,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 1, "n_iterations": 1},
    )
    with pytest.raises(AdapterError):
        PairProbe().run(_behavior(), ctx)


def test_requires_judge_client(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=True),
        fake_adapter(_json("p")),
        None,
        params={"n_streams": 1, "n_iterations": 1},
    )
    with pytest.raises(AdapterError):
        PairProbe().run(_behavior(), ctx)


def test_target_receives_parsed_prompt(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter([_json("PARSED")])
    ctx, _ = _ctx(
        inner,
        fake_judge(success=False),
        attacker,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 1, "n_iterations": 1},
    )
    attempt = PairProbe().run(_behavior(), ctx)
    # target 은 JSON 이 아니라 파싱된 prompt 를 받는다.
    assert inner.calls[0] == ("generate", "PARSED", None)
    assert attempt.final_prompt == "PARSED"


def test_round_robin_three_strategies(fake_adapter, fake_judge) -> None:
    attacker = fake_adapter([_json("p0"), _json("p1"), _json("p2")])
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=False),
        attacker,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 3, "n_iterations": 1},
    )
    PairProbe().run(_behavior(), ctx)
    # 스트림 0/1/2 의 system 메시지가 각각 roleplaying/logical/authority 전략이어야 한다.
    sys0 = attacker.calls[0][1][0].content
    sys1 = attacker.calls[1][1][0].content
    sys2 = attacker.calls[2][1][0].content
    assert "employ roleplaying scenarios" in sys0
    assert "persuade the language model through logical appeal" in sys1
    assert "authority endorsement by referencing reputable authorities" in sys2


def test_early_stop_on_rating_10(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(_json("p"))  # str → 매 호출 동일 JSON
    ctx, counter = _ctx(
        inner,
        fake_judge(success=True),
        attacker,
        fake_adapter("Rating: [[10]]"),
        params={"n_streams": 1, "n_iterations": 3},
    )
    attempt = PairProbe().run(_behavior(), ctx)
    # 첫 iteration 에서 10 → 조기중단: target/attacker 각 1회.
    assert counter.count == 1
    assert attempt.attacker_calls == 1
    assert len(attempt.turns) == 1


def test_success_comes_from_primary_judge(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(_json("p"))
    # 내부 rating 은 낮지만(3), primary judge 가 성공이면 success=True.
    ctx, _ = _ctx(
        inner,
        fake_judge(success=True),
        attacker,
        fake_adapter("Rating: [[3]]"),
        params={"n_streams": 1, "n_iterations": 1},
    )
    attempt = PairProbe().run(_behavior(), ctx)
    assert attempt.success is True
    # 내부 pair_judge 판정도 detections 에 실린다(1~10 스케일).
    assert attempt.detections[1].judge_name == "pair_judge"
    assert attempt.detections[1].score == 3.0


def test_best_score_stream_is_final(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter([_json("P0"), _json("P1")])
    judge_client = fake_adapter(["Rating: [[3]]", "Rating: [[8]]"])
    ctx, _ = _ctx(
        inner,
        fake_judge(success=False),
        attacker,
        judge_client,
        params={"n_streams": 2, "n_iterations": 1},
    )
    attempt = PairProbe().run(_behavior(), ctx)
    # 최고 점수(8) 스트림의 프롬프트가 final.
    assert attempt.final_prompt == "P1"
    assert attempt.detections[1].score == 8.0


def test_keep_last_n_truncates_conversation(fake_adapter, fake_judge) -> None:
    attacker = fake_adapter(_json("p"))
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=False),
        attacker,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 1, "n_iterations": 3, "keep_last_n": 1},
    )
    PairProbe().run(_behavior(), ctx)
    # keep_last_n=1: iteration3 의 attacker.chat 은 system + 직전 2메시지 + 새 user = 4개.
    # (truncation 없으면 6개로 자랐을 것)
    assert len(attacker.calls[2][1]) == 4


def test_json_retry_then_success(fake_adapter, fake_judge) -> None:
    inner = fake_adapter("resp")
    attacker = fake_adapter(["not json at all", _json("P")])
    ctx, counter = _ctx(
        inner,
        fake_judge(success=False),
        attacker,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 1, "n_iterations": 1, "max_n_attack_attempts": 5},
    )
    attempt = PairProbe().run(_behavior(), ctx)
    assert attempt.attacker_calls == 2  # 1 실패 + 1 성공
    assert counter.count == 1  # target 은 성공 후 1회만
    assert attempt.final_prompt == "P"


def test_json_retry_exhausted_raises(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=False),
        fake_adapter("never valid"),
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 1, "n_iterations": 1, "max_n_attack_attempts": 2},
    )
    with pytest.raises(AdapterError):
        PairProbe().run(_behavior(), ctx)


def test_budget_exceeded_propagates(fake_adapter, fake_judge) -> None:
    attacker = fake_adapter(_json("p"))
    ctx, counter = _ctx(
        fake_adapter("r"),
        fake_judge(success=False),
        attacker,
        fake_adapter("Rating: [[1]]"),
        params={"n_streams": 2, "n_iterations": 2},
        limit=2,
    )
    # 4회 target 예정, 예산 2 → 3번째에서 BudgetExceeded.
    with pytest.raises(BudgetExceeded):
        PairProbe().run(_behavior(), ctx)
    assert counter.count == 2


def test_rejects_non_positive_stream_and_iteration_counts(fake_adapter, fake_judge) -> None:
    """퇴화 param 은 bare assert 로 터지지 않고 ConfigError 로 거절된다."""
    for params in ({"n_iterations": 0}, {"n_streams": 0}, {"n_streams": -1}):
        ctx, _ = _ctx(
            fake_adapter("r"),
            fake_judge(success=False),
            fake_adapter(_json("p")),
            fake_adapter("Rating: [[1]]"),
            params=params,
        )
        with pytest.raises(ConfigError):
            PairProbe().run(_behavior(), ctx)


def test_rejects_non_integer_params(fake_adapter, fake_judge) -> None:
    ctx, _ = _ctx(
        fake_adapter("r"),
        fake_judge(success=False),
        fake_adapter(_json("p")),
        fake_adapter("Rating: [[1]]"),
        params={"n_iterations": "many"},
    )
    with pytest.raises(ConfigError):
        PairProbe().run(_behavior(), ctx)
