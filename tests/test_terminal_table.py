"""terminal_table.render_table 검증 — ASCII 요약표 문자열."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.reporting.terminal_table")

from redteam.core import Attempt, Behavior, DetectionResult, Turn  # noqa: E402
from redteam.reporting.aggregate import summarize  # noqa: E402
from redteam.reporting.terminal_table import render_table  # noqa: E402


def _attempt(behavior_id, technique, success, target_calls, detections):
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
def summary():
    attempts = [
        _attempt(
            "b1",
            "flip_attack",
            True,
            1,
            (DetectionResult(True, "strong_reject", 0.8, ("weapons",)),),
        ),
        _attempt("b2", "pair", False, 4, (DetectionResult(False, "refusal_match"),)),
    ]
    behaviors = [
        Behavior(id="b1", prompt="p", domain="cyber"),
        Behavior(id="b2", prompt="p", domain="ot_ics"),
    ]
    return summarize(attempts, behaviors)


def test_returns_str(summary):
    assert isinstance(render_table(summary), str)


def test_has_header_columns(summary):
    out = render_table(summary)
    assert "technique" in out
    assert "ASR@B" in out
    assert "efficiency" in out
    assert "SR_avg" in out


def test_has_technique_rows(summary):
    out = render_table(summary)
    assert "flip_attack" in out
    assert "pair" in out


def test_has_domain_section(summary):
    out = render_table(summary)
    assert "cyber" in out
    assert "ot_ics" in out


def test_has_category_section(summary):
    out = render_table(summary)
    assert "weapons" in out


def test_empty_summary_does_not_crash():
    out = render_table(summarize([], None))
    assert isinstance(out, str)
    assert "technique" in out
