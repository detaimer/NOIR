"""CrescendoRefusal — PyRIT SelfAskRefusalScorer (vendor 프롬프트 재사용).

Azure/PyRIT @ 004d079 `refusal_default.yaml`/`refusal_strict.yaml` +
`self_ask_refusal_scorer.py`. 거부면 refusal, 성공(success)=비거부(=응답이 목표에 응함).
Crescendo probe 는 이 판정으로 백트래킹 여부를 정한다(probe 는 vendor.parse_refusal 직접 사용).
"""

from __future__ import annotations

from redteam.core import Adapter, Behavior, DetectionResult, Detector, Turn
from redteam.vendor import crescendo_refusal_system, crescendo_refusal_user, parse_refusal


class CrescendoRefusal(Detector):
    """응답이 거부인지 판정하는 judge (success=비거부)."""

    name = "crescendo_refusal"

    def __init__(self, judge_client: Adapter | None, strict: bool = False) -> None:
        """judge_client(Adapter)와 strict(safe-completion 도 거부로 볼지)를 보관한다."""
        self._client = judge_client
        self._strict = strict

    def judge(
        self,
        behavior: Behavior | None,
        prompt: str,
        response: str,
        conversation: list[Turn] | None = None,
    ) -> DetectionResult:
        """refusal scorer 를 호출해 거부 여부를 판정한다(성공=비거부)."""
        objective = behavior.prompt if behavior is not None else prompt
        raw = (
            self._client.generate(
                crescendo_refusal_user(objective, response),
                system=crescendo_refusal_system(self._strict),
            )
            or ""
        )
        refused = parse_refusal(raw)
        return DetectionResult(
            success=not refused,
            judge_name="crescendo_refusal",
            categories=("refusal",) if refused else (),
            rationale=raw or None,
        )
