"""공용 레코드 타입 — 불변(frozen) dataclass 로 값 동등성·해시 가능.

역할 패키지(probes/adapters/detectors/reporting/behaviors)와 runner 가 주고받는 데이터 계약.
컬렉션 필드는 tuple 로 두어 불변·해시 가능성을 유지한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    """대화 메시지 역할 (str 혼합 enum — 문자열 비교/직렬화 편의)."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True)
class Message:
    """단일 대화 메시지."""

    role: Role
    content: str


@dataclass(frozen=True)
class Behavior:
    """시드 유해요청 한 건 + taxonomy 메타.

    OT/ICS 는 특별취급 없이 `domain="ot_ics"` + `attack-ics:*` 태그로 표현한다.
    """

    id: str
    prompt: str
    domain: str
    subcat: str = ""
    tags: tuple[str, ...] = ()
    source: str = "builtin"


@dataclass(frozen=True)
class Turn:
    """한 턴의 (프롬프트, 응답) 쌍. 멀티턴 기법에서 conversation 을 구성."""

    prompt: str
    response: str


@dataclass(frozen=True)
class DetectionResult:
    """judge(detector) 한 개의 구조화 판정 결과.

    이진 judge 는 `score=None`, 등급 judge(StrongREJECT)는 0~1 `score` 를 채운다.
    """

    success: bool
    judge_name: str
    score: float | None = None
    categories: tuple[str, ...] = ()
    rationale: str | None = None


@dataclass(frozen=True)
class Attempt:
    """한 (behavior × technique) 시도의 전체 기록.

    `detections` 는 모든 judge 의 결과, `success` 는 primary judge(detectors[0]) 기준.
    `target_calls` 가 Fair-ASR 비교 단위(BudgetedTarget 가 집계).
    """

    behavior_id: str
    technique: str
    turns: tuple[Turn, ...]
    final_prompt: str
    final_response: str
    detections: tuple[DetectionResult, ...]
    success: bool
    target_calls: int
    attacker_calls: int = 0
    judge_calls: int = 0
    budget_exhausted: bool = False
    error: str | None = None
