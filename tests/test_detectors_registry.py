"""detectors 패키지의 DETECTORS 레지스트리·팩토리 규약 테스트."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.detectors")

from redteam.core import Detector
from redteam.detectors import (
    DETECTORS,
    LlamaGuard,
    RefusalMatch,
    StrongReject,
)


def test_registry_has_three_detectors() -> None:
    assert set(DETECTORS) == {"refusal_match", "llama_guard", "strong_reject"}


def test_refusal_match_factory_ignores_client_and_takes_params() -> None:
    det = DETECTORS["refusal_match"](judge_client=None, extra_phrases=("nope",))
    assert isinstance(det, RefusalMatch)
    assert isinstance(det, Detector)
    assert det.name == "refusal_match"


def test_llama_guard_factory_injects_client(fake_adapter) -> None:
    client = fake_adapter(responses="safe")
    det = DETECTORS["llama_guard"](judge_client=client)
    assert isinstance(det, LlamaGuard)
    # 주입된 client 로 실제 판정이 동작하는지 스모크.
    result = det.judge(None, "q", "r")
    assert result.success is False


def test_strong_reject_factory_injects_client_and_params(fake_adapter) -> None:
    client = fake_adapter(responses="refused: 0\nspecific: 5\nconvincing: 5")
    det = DETECTORS["strong_reject"](judge_client=client, threshold=0.9)
    assert isinstance(det, StrongReject)
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert result.score == pytest.approx(1.0)
