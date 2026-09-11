"""probes — 공격 기법 플러그인. 정적(one-shot) 기법과 PROBES 레지스트리를 재노출."""

from __future__ import annotations

from collections.abc import Callable

from redteam.core import Probe
from redteam.probes.crescendo_probe import CrescendoProbe
from redteam.probes.pair_probe import PairProbe
from redteam.probes.static_probe import StaticProbe
from redteam.probes.transforms import (
    flip_attack,
    many_shot,
    past_tense,
    reverse_text,
    to_base64,
)

# 이름 → zero-arg 팩토리 `() -> Probe` (registry/runner 가 이름으로 조회해 조합).
PROBES: dict[str, Callable[[], Probe]] = {
    "past_tense": lambda: StaticProbe(past_tense, "past_tense"),
    "base64": lambda: StaticProbe(to_base64, "base64"),
    "flip_attack": lambda: StaticProbe(flip_attack, "flip_attack"),
    "many_shot": lambda: StaticProbe(many_shot, "many_shot"),
    "pair": lambda: PairProbe(),
    "crescendo": lambda: CrescendoProbe(),
}

__all__ = [
    "StaticProbe",
    "PairProbe",
    "CrescendoProbe",
    "PROBES",
    "past_tense",
    "to_base64",
    "flip_attack",
    "many_shot",
    "reverse_text",
]
