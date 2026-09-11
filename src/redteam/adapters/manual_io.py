"""ManualIOAdapter — API 없는 챗봇을 사람이 중계하는 어댑터(멀티턴 지원)."""

from __future__ import annotations

from collections.abc import Callable

from redteam.core import Message


class ManualIOAdapter:
    """프롬프트를 output_fn 으로 보여주고 input_fn 으로 응답을 읽는 사람-중계 Adapter."""

    def __init__(
        self,
        input_fn: Callable[[], str] = input,
        output_fn: Callable[[str], object] = print,
        sentinel: str = ".",
        name: str = "manual",
    ) -> None:
        """input_fn/output_fn 을 주입(테스트 결정론), sentinel 단독 줄로 응답 종료."""
        self.input_fn = input_fn
        self.output_fn = output_fn
        self.sentinel = sentinel
        self.name = name

    def generate(self, prompt: str, system: str | None = None) -> str:
        """system(옵션)+프롬프트를 보여주고 사람이 입력한 응답을 반환한다."""
        if system:
            self.output_fn(f"[system] {system}")
        self.output_fn(f"[prompt] {prompt}")
        return self._read_response()

    def chat(self, messages: list[Message]) -> str:
        """대화(최소한 최신 user 메시지)를 보여주고 사람이 입력한 응답을 반환한다."""
        for m in messages:
            self.output_fn(f"{m.role.value}: {m.content}")
        return self._read_response()

    def _read_response(self) -> str:
        """sentinel 단독 줄 또는 입력 소진(EOF/StopIteration)까지 줄을 모아 반환한다."""
        lines: list[str] = []
        while True:
            try:
                line = self.input_fn()
            except (EOFError, StopIteration):
                break
            if line == self.sentinel:
                break
            lines.append(line)
        return "\n".join(lines)
