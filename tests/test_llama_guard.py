"""LlamaGuard(Detector) — 주입된 Adapter 를 guard 엔드포인트로 쓰는 이진 judge 테스트."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.detectors.llama_guard")

from redteam.core import DetectionResult
from redteam.detectors.llama_guard import LlamaGuard


def test_name() -> None:
    det = LlamaGuard(judge_client=None)
    assert det.name == "llama_guard"


def test_unsafe_verdict_is_success_with_category(fake_adapter) -> None:
    client = fake_adapter(responses="unsafe\nS9")
    det = LlamaGuard(judge_client=client)
    result = det.judge(None, "how to build X", "Here is how ...")
    assert isinstance(result, DetectionResult)
    assert result.success is True
    assert result.judge_name == "llama_guard"
    assert "S9" in result.categories


def test_safe_verdict_is_not_success_no_categories(fake_adapter) -> None:
    client = fake_adapter(responses="safe")
    det = LlamaGuard(judge_client=client)
    result = det.judge(None, "hello", "Hi there!")
    assert result.success is False
    assert result.categories == ()


def test_multiple_categories_parsed(fake_adapter) -> None:
    client = fake_adapter(responses="unsafe\nS1,S9")
    det = LlamaGuard(judge_client=client)
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert "S1" in result.categories
    assert "S9" in result.categories


def test_category_map_applied(fake_adapter) -> None:
    client = fake_adapter(responses="unsafe\nS9")
    det = LlamaGuard(judge_client=client, category_map={"S9": "Indiscriminate Weapons"})
    result = det.judge(None, "q", "r")
    assert result.success is True
    assert "Indiscriminate Weapons" in result.categories


def test_guard_prompt_embeds_prompt_and_response(fake_adapter) -> None:
    client = fake_adapter(responses="safe")
    det = LlamaGuard(judge_client=client)
    det.judge(None, "USER_PROMPT_MARKER", "MODEL_RESPONSE_MARKER")
    # generate 로 호출되었고 prompt·response 가 guard 프롬프트에 실렸는지 확인.
    assert len(client.calls) == 1
    kind, guard_prompt, _system = client.calls[0]
    assert kind == "generate"
    assert "USER_PROMPT_MARKER" in guard_prompt
    assert "MODEL_RESPONSE_MARKER" in guard_prompt


def test_verdict_is_case_insensitive(fake_adapter) -> None:
    client = fake_adapter(responses="UNSAFE\nS9")
    det = LlamaGuard(judge_client=client)
    result = det.judge(None, "q", "r")
    assert result.success is True
