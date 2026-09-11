"""테스트 공용 fake·픽스처 — 네트워크/비결정 없이 결정론적으로 테스트.

sub-agent 는 이 파일을 **수정하지 말 것**(병합 충돌 방지). 테스트별 픽스처/헬퍼는 각자
`tests/test_<name>.py` 안에 두고, 여기 것은 재사용만 한다.
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from redteam.core import (
    Attempt,
    Behavior,
    DetectionResult,
    Detector,
    Message,
    Turn,
)


class FakeAdapter:
    """scripted Adapter — 미리 정한 응답을 반환하고 호출을 기록한다(네트워크 없음).

    responses:
      - None  → 항상 "fake-response"
      - str   → 항상 그 문자열
      - list  → 순서대로 소비, 소진 후 마지막 값을 반복
    """

    def __init__(self, responses: str | Sequence[str] | None = None, name: str = "fake") -> None:
        self.name = name
        self._responses = responses
        self.calls: list[tuple] = []

    def _next(self, payload: tuple) -> str:
        self.calls.append(payload)
        if self._responses is None:
            return "fake-response"
        if isinstance(self._responses, str):
            return self._responses
        idx = len(self.calls) - 1
        if not self._responses:
            return "fake-response"
        return self._responses[idx] if idx < len(self._responses) else self._responses[-1]

    def chat(self, messages: list[Message]) -> str:
        return self._next(("chat", list(messages)))

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._next(("generate", prompt, system))


class FakeJudge(Detector):
    """scripted Detector — 고정 결과 또는 k번째(1-based) 호출부터 성공."""

    def __init__(
        self,
        name: str = "fake_judge",
        *,
        success: bool = False,
        score: float | None = None,
        success_on_call: int | None = None,
        categories: Sequence[str] = (),
    ) -> None:
        self.name = name
        self._success = success
        self._score = score
        self._success_on_call = success_on_call
        self._categories = tuple(categories)
        self.calls = 0

    def judge(self, behavior, prompt, response, conversation=None) -> DetectionResult:
        self.calls += 1
        ok = (
            self.calls >= self._success_on_call
            if self._success_on_call is not None
            else self._success
        )
        return DetectionResult(
            success=ok,
            judge_name=self.name,
            score=self._score,
            categories=self._categories,
        )


def make_attempt(
    *,
    behavior_id: str = "b1",
    technique: str = "flip_attack",
    success: bool = False,
    target_calls: int = 1,
    detections: Sequence[DetectionResult] | None = None,
    **kwargs,
) -> Attempt:
    """reporting 등에서 쓰는 Attempt 팩토리 (합리적 기본값)."""
    if detections is None:
        detections = (DetectionResult(success=success, judge_name="refusal_match"),)
    return Attempt(
        behavior_id=behavior_id,
        technique=technique,
        turns=kwargs.pop("turns", (Turn(prompt="p", response="r"),)),
        final_prompt=kwargs.pop("final_prompt", "p"),
        final_response=kwargs.pop("final_response", "r"),
        detections=tuple(detections),
        success=success,
        target_calls=target_calls,
        **kwargs,
    )


@pytest.fixture
def fake_adapter():
    """FakeAdapter 팩토리 픽스처."""
    return FakeAdapter


@pytest.fixture
def fake_judge():
    """FakeJudge 팩토리 픽스처."""
    return FakeJudge


@pytest.fixture
def sample_behavior() -> Behavior:
    return Behavior(
        id="b1",
        prompt="샘플 유해요청(추상 paraphrase)",
        domain="cyber",
        subcat="malware",
        tags=("owasp-llm:LLM01", "attack:T1059"),
        source="builtin",
    )


@pytest.fixture
def sample_behaviors() -> list[Behavior]:
    return [
        Behavior(id="b1", prompt="p1", domain="cyber", tags=("owasp-llm:LLM01",)),
        Behavior(id="b2", prompt="p2", domain="ot_ics", tags=("attack-ics:T0836",)),
        Behavior(id="b3", prompt="p3", domain="privacy", tags=("owasp-llm:LLM06",)),
    ]
