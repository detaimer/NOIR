"""detectors 패키지의 DETECTORS 레지스트리·팩토리 규약 테스트."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.detectors")

from redteam.core import Detector
from redteam.detectors import (
    DETECTORS,
    CrescendoObjective,
    CrescendoRefusal,
    LlamaGuard,
    PairJudge,
    RefusalMatch,
    StrongReject,
)


def test_registry_has_all_detectors() -> None:
    assert set(DETECTORS) == {
        "refusal_match",
        "llama_guard",
        "strong_reject",
        "pair_judge",
        "crescendo_refusal",
        "crescendo_objective",
    }


def test_refusal_match_factory_ignores_client_and_takes_params() -> None:
    det = DETECTORS["refusal_match"](judge_client=None, extra_phrases=("nope",))
    assert isinstance(det, RefusalMatch)
    assert isinstance(det, Detector)
    assert det.name == "refusal_match"


def test_llama_guard_factory_injects_client(fake_adapter) -> None:
    client = fake_adapter(responses="safe")
    det = DETECTORS["llama_guard"](judge_client=client)
    assert isinstance(det, LlamaGuard)
    result = det.judge(None, "q", "r")
    assert result.success is False


def test_strong_reject_factory_injects_client_and_params(fake_adapter) -> None:
    client = fake_adapter(responses="refused: 0\nspecific: 5\nconvincing: 5")
    det = DETECTORS["strong_reject"](judge_client=client, threshold=0.9)
    assert isinstance(det, StrongReject)
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert result.score == pytest.approx(1.0)


def test_pair_judge_factory_injects_client_and_params(fake_adapter) -> None:
    client = fake_adapter(responses="Rating: [[7]]")
    det = DETECTORS["pair_judge"](judge_client=client, threshold=5)
    assert isinstance(det, PairJudge)
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert result.score == 7.0


def test_crescendo_refusal_factory_injects_client(fake_adapter) -> None:
    client = fake_adapter(responses='{"score_value": "True"}')
    det = DETECTORS["crescendo_refusal"](judge_client=client, strict=True)
    assert isinstance(det, CrescendoRefusal)
    assert det.judge(None, "q", "r").success is False  # refusal → not success


def test_crescendo_objective_factory_injects_client_and_params(fake_adapter) -> None:
    client = fake_adapter(responses='{"score_value": "90"}')
    det = DETECTORS["crescendo_objective"](judge_client=client, threshold=0.8)
    assert isinstance(det, CrescendoObjective)
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert result.score == pytest.approx(0.9)
