"""플러그인 계약 — Adapter(Protocol)·Detector(ABC)·Probe(ABC)·ProbeContext.

DI 원칙: 역할 패키지는 이 계약(=core)에만 의존하고, 구체 협력자는 run 시 주입받는다.
Adapter 는 구조적(Protocol)이라 fake 가 상속 없이도 만족하고, Detector/Probe 는 ABC 로
직접 인스턴스화를 막는다.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from redteam.core.records import Attempt, Behavior, DetectionResult, Message, Turn


@runtime_checkable
class Adapter(Protocol):
    """타깃/attacker/judge 엔드포인트 클라이언트. stateless — 히스토리는 caller 가 관리."""

    name: str

    def chat(self, messages: list[Message]) -> str:
        """멀티턴 메시지 목록을 보내고 assistant 응답 텍스트를 받는다."""
        ...

    def generate(self, prompt: str, system: str | None = None) -> str:
        """단일 프롬프트(+선택 system)를 보내고 응답 텍스트를 받는다."""
        ...


class Detector(ABC):
    """성공 판정(judge) — 구조화된 DetectionResult 를 반환하는 pluggable 컴포넌트."""

    name: str = "detector"

    @abstractmethod
    def judge(
        self,
        behavior: Behavior | None,
        prompt: str,
        response: str,
        conversation: list[Turn] | None = None,
    ) -> DetectionResult:
        """응답의 성공/유해 여부를 판정한다."""
        raise NotImplementedError


class Probe(ABC):
    """공격 기법 — 모든 tier(정적/PAIR/Crescendo)가 단일 run 계약으로 수렴."""

    name: str = "probe"
    uses_attacker: bool = False
    uses_judge: bool = True
    default_turns: int = 1

    @abstractmethod
    def run(self, behavior: Behavior, ctx: ProbeContext) -> Attempt:
        """behavior 에 기법을 적용해 한 번의 Attempt 를 생성한다."""
        raise NotImplementedError


@dataclass
class ProbeContext:
    """probe.run 에 주입되는 실행 컨텍스트 — 협력자(주입)와 실행 파라미터."""

    target: Adapter
    judge: Detector
    attacker: Adapter | None
    max_turns: int
    max_attempts: int
    rng: random.Random
