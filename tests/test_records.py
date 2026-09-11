"""core.records 레코드 타입 — 생성·불변(frozen)·동등성 검증."""

from __future__ import annotations

import dataclasses

import pytest

rec = pytest.importorskip("redteam.core.records")


def test_role_enum_values():
    assert rec.Role.SYSTEM.value == "system"
    assert rec.Role.USER.value == "user"
    assert rec.Role.ASSISTANT.value == "assistant"
    # str-enum: 문자열로도 비교 가능
    assert rec.Role.USER == "user"


def test_message_create_and_equality():
    a = rec.Message(role=rec.Role.USER, content="hi")
    b = rec.Message(role=rec.Role.USER, content="hi")
    assert a == b
    assert a.role == rec.Role.USER
    assert a.content == "hi"


def test_message_is_frozen():
    m = rec.Message(role=rec.Role.USER, content="hi")
    with pytest.raises(dataclasses.FrozenInstanceError):
        m.content = "bye"  # type: ignore[misc]


def test_behavior_defaults_and_fields():
    b = rec.Behavior(id="b1", prompt="do x", domain="cyber")
    assert b.id == "b1"
    assert b.prompt == "do x"
    assert b.domain == "cyber"
    # 선택 필드 기본값
    assert b.subcat == ""
    assert b.tags == ()
    assert b.source == "builtin"


def test_behavior_with_tags_equality():
    b1 = rec.Behavior(
        id="b1",
        prompt="p",
        domain="ot_ics",
        subcat="scada",
        tags=("attack-ics:T0836",),
        source="jbb",
    )
    b2 = rec.Behavior(
        id="b1",
        prompt="p",
        domain="ot_ics",
        subcat="scada",
        tags=("attack-ics:T0836",),
        source="jbb",
    )
    assert b1 == b2
    assert b1.tags == ("attack-ics:T0836",)


def test_behavior_is_frozen():
    b = rec.Behavior(id="b1", prompt="p", domain="cyber")
    with pytest.raises(dataclasses.FrozenInstanceError):
        b.prompt = "other"  # type: ignore[misc]


def test_turn_create():
    t = rec.Turn(prompt="q", response="a")
    assert t.prompt == "q"
    assert t.response == "a"
    assert t == rec.Turn(prompt="q", response="a")


def test_detection_result_binary_and_graded():
    binary = rec.DetectionResult(success=True, judge_name="refusal_match")
    assert binary.success is True
    assert binary.judge_name == "refusal_match"
    assert binary.score is None
    assert binary.categories == ()
    assert binary.rationale is None

    graded = rec.DetectionResult(
        success=True,
        judge_name="strong_reject",
        score=0.8,
        categories=("S9",),
        rationale="specific and convincing",
    )
    assert graded.score == 0.8
    assert graded.categories == ("S9",)
    assert graded.rationale == "specific and convincing"


def test_detection_result_is_frozen():
    d = rec.DetectionResult(success=False, judge_name="llama_guard")
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.success = True  # type: ignore[misc]


def test_attempt_minimal_and_defaults():
    det = rec.DetectionResult(success=True, judge_name="refusal_match")
    a = rec.Attempt(
        behavior_id="b1",
        technique="flip_attack",
        turns=(rec.Turn(prompt="p", response="r"),),
        final_prompt="p",
        final_response="r",
        detections=(det,),
        success=True,
        target_calls=1,
    )
    assert a.behavior_id == "b1"
    assert a.technique == "flip_attack"
    assert a.target_calls == 1
    # 기본값
    assert a.attacker_calls == 0
    assert a.judge_calls == 0
    assert a.budget_exhausted is False
    assert a.error is None
    assert a.detections[0] is det


def test_attempt_equality_and_frozen():
    det = rec.DetectionResult(success=False, judge_name="refusal_match")
    kwargs = dict(
        behavior_id="b1",
        technique="pair",
        turns=(),
        final_prompt="p",
        final_response="r",
        detections=(det,),
        success=False,
        target_calls=3,
        attacker_calls=3,
        judge_calls=3,
    )
    a1 = rec.Attempt(**kwargs)
    a2 = rec.Attempt(**kwargs)
    assert a1 == a2
    with pytest.raises(dataclasses.FrozenInstanceError):
        a1.success = True  # type: ignore[misc]
