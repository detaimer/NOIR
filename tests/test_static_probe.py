"""StaticProbe — 변환 적용·단일 target 호출·판정 임베드 검증 (DI 컨텍스트)."""

from __future__ import annotations

import random

import pytest

pytest.importorskip("redteam.probes.static_probe")

from redteam.core import Behavior, ProbeContext  # noqa: E402
from redteam.probes.static_probe import StaticProbe  # noqa: E402


def _ctx(target, judge) -> ProbeContext:
    return ProbeContext(
        target=target,
        judge=judge,
        attacker=None,
        max_turns=1,
        max_attempts=1,
        rng=random.Random(0),
    )


def _behavior() -> Behavior:
    return Behavior(id="b1", prompt="original request", domain="cyber")


def test_static_probe_attrs() -> None:
    probe = StaticProbe(lambda p: p, "identity")
    assert probe.name == "identity"
    assert probe.uses_attacker is False
    assert probe.uses_judge is True
    assert probe.default_turns == 1


def test_transform_applied_to_target(fake_adapter, fake_judge) -> None:
    target = fake_adapter("resp")
    probe = StaticProbe(lambda p: f"[X]{p}", "wrap")
    attempt = probe.run(_behavior(), _ctx(target, fake_judge(success=True)))

    # target 이 변환된 프롬프트를 받았는지 calls 로 확인.
    assert target.calls == [("generate", "[X]original request", None)]
    assert attempt.final_prompt == "[X]original request"
    assert attempt.final_response == "resp"


def test_single_target_call_and_embedded_detection(fake_adapter, fake_judge) -> None:
    probe = StaticProbe(lambda p: p, "identity")
    judge = fake_judge(name="fake_judge", success=True, score=0.9)
    attempt = probe.run(_behavior(), _ctx(fake_adapter("r"), judge))

    assert attempt.target_calls == 1
    assert attempt.judge_calls == 1
    assert len(attempt.detections) == 1
    det = attempt.detections[0]
    assert det.judge_name == "fake_judge"
    assert det.score == 0.9
    # 단일 턴이 기록된다.
    assert len(attempt.turns) == 1
    assert attempt.turns[0].prompt == "original request"
    assert attempt.turns[0].response == "r"
    assert attempt.technique == "identity"
    assert attempt.behavior_id == "b1"


@pytest.mark.parametrize("judge_success", [True, False])
def test_success_mirrors_judge(fake_adapter, fake_judge, judge_success: bool) -> None:
    probe = StaticProbe(lambda p: p, "identity")
    attempt = probe.run(_behavior(), _ctx(fake_adapter("r"), fake_judge(success=judge_success)))
    assert attempt.success is judge_success
    assert attempt.detections[0].success is judge_success


def test_registry_factories_build_probes() -> None:
    from redteam.probes import PROBES

    # 정적 tier 4종이 등록돼 있어야 한다(반복형/멀티턴 probe 가 추가돼도 부분집합으로 유지).
    static_keys = {"past_tense", "base64", "flip_attack", "many_shot"}
    assert static_keys <= set(PROBES)
    for key in static_keys:
        probe = PROBES[key]()
        assert isinstance(probe, StaticProbe)
        assert probe.name == key
        assert probe.uses_judge is True
        assert probe.uses_attacker is False


def test_registry_probe_transforms_prompt(fake_adapter, fake_judge) -> None:
    from redteam.probes import PROBES

    target = fake_adapter("r")
    probe = PROBES["base64"]()
    attempt = probe.run(_behavior(), _ctx(target, fake_judge(success=False)))
    # base64 probe 는 원문을 그대로 target 에 넘기지 않는다.
    assert attempt.final_prompt != "original request"
    assert attempt.target_calls == 1
