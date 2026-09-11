"""aggregate.summarize 순수 집계 검증 — 수제 attempts 로 정확 수치 assert."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.reporting.aggregate")

from redteam.core import Attempt, Behavior, DetectionResult, Turn  # noqa: E402
from redteam.reporting.aggregate import Summary, summarize  # noqa: E402


def _dr(success: bool, name: str, score=None, categories=()) -> DetectionResult:
    return DetectionResult(
        success=success, judge_name=name, score=score, categories=tuple(categories)
    )


def _attempt(
    behavior_id: str,
    technique: str,
    success: bool,
    target_calls: int,
    detections: tuple[DetectionResult, ...],
) -> Attempt:
    return Attempt(
        behavior_id=behavior_id,
        technique=technique,
        turns=(Turn(prompt="p", response="r"),),
        final_prompt="p",
        final_response="r",
        detections=detections,
        success=success,
        target_calls=target_calls,
    )


@pytest.fixture
def behaviors() -> list[Behavior]:
    return [
        Behavior(id="b1", prompt="p1", domain="cyber"),
        Behavior(id="b2", prompt="p2", domain="ot_ics"),
        Behavior(id="b3", prompt="p3", domain="privacy"),
    ]


@pytest.fixture
def attempts() -> list[Attempt]:
    return [
        # flip_attack: n=3, successes=2, calls sum=6
        _attempt(
            "b1",
            "flip_attack",
            True,
            1,
            (_dr(True, "refusal_match"), _dr(True, "strong_reject", 0.8, ("weapons",))),
        ),
        _attempt(
            "b2",
            "flip_attack",
            True,
            3,
            (_dr(True, "refusal_match"), _dr(True, "strong_reject", 0.6, ("cyber",))),
        ),
        _attempt("b1", "flip_attack", False, 2, (_dr(False, "refusal_match"),)),
        # pair: n=2, successes=1, calls sum=10
        _attempt(
            "b2",
            "pair",
            True,
            4,
            (_dr(True, "refusal_match"), _dr(True, "strong_reject", 0.4, ("cyber",))),
        ),
        _attempt(
            "b3",
            "pair",
            False,
            6,
            (_dr(False, "refusal_match"), _dr(True, "llama_guard", None, ("privacy",))),
        ),
    ]


def test_returns_summary_instance(attempts, behaviors):
    assert isinstance(summarize(attempts, behaviors), Summary)


def test_overall(attempts, behaviors):
    s = summarize(attempts, behaviors)
    assert s.overall["total"] == 5
    assert s.overall["successes"] == 3
    assert s.overall["asr"] == pytest.approx(0.6)


def test_per_technique_flip_attack(attempts, behaviors):
    t = summarize(attempts, behaviors).per_technique["flip_attack"]
    assert t["n"] == 3
    assert t["successes"] == 2
    assert t["asr"] == pytest.approx(2 / 3)
    assert t["avg_target_calls"] == pytest.approx(2.0)
    assert t["efficiency"] == pytest.approx(2 / 6)
    assert t["strong_reject_avg"] == pytest.approx(0.7)


def test_per_technique_pair(attempts, behaviors):
    t = summarize(attempts, behaviors).per_technique["pair"]
    assert t["n"] == 2
    assert t["successes"] == 1
    assert t["asr"] == pytest.approx(0.5)
    assert t["avg_target_calls"] == pytest.approx(5.0)
    assert t["efficiency"] == pytest.approx(0.1)
    assert t["strong_reject_avg"] == pytest.approx(0.4)


def test_per_domain(attempts, behaviors):
    d = summarize(attempts, behaviors).per_domain
    assert d["cyber"] == {"n": 2, "successes": 1, "asr": pytest.approx(0.5)}
    assert d["ot_ics"] == {"n": 2, "successes": 2, "asr": pytest.approx(1.0)}
    assert d["privacy"] == {"n": 1, "successes": 0, "asr": pytest.approx(0.0)}


def test_per_category(attempts, behaviors):
    c = summarize(attempts, behaviors).per_category
    assert c == {"weapons": 1, "cyber": 2, "privacy": 1}


def test_vulnerable_top3(attempts, behaviors):
    # asr desc, tie by count desc then name asc: ot_ics(1.0,2), cyber(0.5,2), privacy(0.0,1)
    assert summarize(attempts, behaviors).vulnerable_top3 == ["ot_ics", "cyber", "privacy"]


def test_judge_agreement(attempts, behaviors):
    # 4/5 agree; only pair/privacy disagrees (refusal_match False vs llama_guard True)
    assert summarize(attempts, behaviors).judge_agreement == pytest.approx(0.8)


def test_behaviors_accepts_dict(attempts, behaviors):
    as_dict = {b.id: b for b in behaviors}
    assert summarize(attempts, as_dict).per_domain == summarize(attempts, behaviors).per_domain


def test_unknown_domain_when_behavior_missing():
    a = _attempt("ghost", "flip_attack", True, 1, (_dr(True, "refusal_match"),))
    s = summarize([a], behaviors=None)
    assert s.per_domain["unknown"] == {"n": 1, "successes": 1, "asr": pytest.approx(1.0)}


def test_strong_reject_avg_zero_when_absent():
    a = _attempt("b1", "flip_attack", True, 1, (_dr(True, "refusal_match"),))
    s = summarize([a], [Behavior(id="b1", prompt="p", domain="cyber")])
    assert s.per_technique["flip_attack"]["strong_reject_avg"] == 0.0


def test_efficiency_guard_zero_calls():
    a = _attempt("b1", "flip_attack", False, 0, (_dr(False, "refusal_match"),))
    s = summarize([a], None)
    assert s.per_technique["flip_attack"]["efficiency"] == 0.0


def test_single_detection_counts_as_agreement():
    a = _attempt("b1", "flip_attack", True, 1, (_dr(True, "refusal_match"),))
    assert summarize([a], None).judge_agreement == pytest.approx(1.0)


def test_empty_attempts():
    s = summarize([], None)
    assert s.overall == {"total": 0, "successes": 0, "asr": 0.0}
    assert s.per_technique == {}
    assert s.per_domain == {}
    assert s.per_category == {}
    assert s.vulnerable_top3 == []
    assert s.judge_agreement == 1.0
