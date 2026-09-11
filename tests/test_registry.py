"""registry — 역할 dict 취합·이름 해석, unknown→UnknownComponent(추천), available()."""

from __future__ import annotations

import pytest

reg = pytest.importorskip("redteam.registry")
from redteam.core import Detector, Probe, UnknownComponent  # noqa: E402


def test_get_probe_known_returns_instance():
    p = reg.get_probe("flip_attack")
    assert isinstance(p, Probe)
    assert p.name == "flip_attack"
    # 매 호출 새 인스턴스
    assert reg.get_probe("flip_attack") is not p


def test_get_probe_unknown_raises_with_available():
    with pytest.raises(UnknownComponent) as ei:
        reg.get_probe("nope")
    assert ei.value.role == "probe"
    assert "flip_attack" in ei.value.available
    assert "nope" in str(ei.value)


def test_get_detector_no_client():
    d = reg.get_detector("refusal_match")
    assert isinstance(d, Detector)
    assert d.name == "refusal_match"


def test_get_detector_with_client_and_params(fake_adapter):
    client = fake_adapter(responses="safe")
    d = reg.get_detector("llama_guard", judge_client=client)
    assert isinstance(d, Detector)
    assert d.name == "llama_guard"


def test_get_detector_unknown_raises():
    with pytest.raises(UnknownComponent) as ei:
        reg.get_detector("nope")
    assert ei.value.role == "detector"
    assert "refusal_match" in ei.value.available


def test_get_adapter_known_returns_factory():
    factory = reg.get_adapter("http_openai")
    assert callable(factory)
    assert factory.__name__ == "HttpOpenAIAdapter"


def test_get_adapter_unknown_raises():
    with pytest.raises(UnknownComponent) as ei:
        reg.get_adapter("nope")
    assert ei.value.role == "adapter"
    assert "manual" in ei.value.available


def test_available_lists_all_roles():
    av = reg.available()
    assert "flip_attack" in av["probe"]
    assert "refusal_match" in av["detector"]
    assert "http_openai" in av["adapter"]
