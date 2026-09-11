"""StaticProbe — one-shot 정적 기법: 프롬프트 변환 → 단일 target 호출 → judge."""

from __future__ import annotations

from collections.abc import Callable

from redteam.core import Attempt, Behavior, Probe, ProbeContext, Turn


class StaticProbe(Probe):
    """순수 transform 하나를 적용해 단일 턴으로 실행하는 정적 probe."""

    uses_attacker = False
    uses_judge = True
    default_turns = 1

    def __init__(self, transform: Callable[[str], str], name: str) -> None:
        self.transform = transform
        self.name = name

    def run(self, behavior: Behavior, ctx: ProbeContext) -> Attempt:
        """behavior.prompt 을 변환해 한 번 호출하고 판정을 임베드한 Attempt 를 만든다."""
        p = self.transform(behavior.prompt)
        resp = ctx.target.generate(p)
        det = ctx.judge.judge(behavior, p, resp)
        return Attempt(
            behavior_id=behavior.id,
            technique=self.name,
            turns=(Turn(prompt=p, response=resp),),
            final_prompt=p,
            final_response=resp,
            detections=(det,),
            success=det.success,
            target_calls=1,
            judge_calls=1,
        )
