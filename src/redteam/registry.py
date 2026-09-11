"""레지스트리 — 역할 패키지의 name→factory dict 를 취합해 이름으로 조회한다.

방향: registry 가 역할 패키지를 import 한다(역방향 금지). unknown 이름은 UnknownComponent 로
유효 목록을 제시한다. adapter 는 구성 인자가 종류마다 달라 팩토리(클래스)를 돌려주고
runner 가 구성한다. probe/detector 는 여기서 인스턴스를 만든다.
"""

from __future__ import annotations

from collections.abc import Callable

from redteam.adapters import ADAPTERS
from redteam.core import Detector, Probe, UnknownComponent
from redteam.detectors import DETECTORS
from redteam.probes import PROBES


def _resolve(role: str, name: str, table: dict) -> object:
    if name not in table:
        raise UnknownComponent(role, name, tuple(sorted(table)))
    return table[name]


def get_probe(name: str) -> Probe:
    """이름으로 새 Probe 인스턴스를 만든다."""
    factory = _resolve("probe", name, PROBES)
    return factory()


def get_detector(name: str, judge_client=None, **params) -> Detector:
    """이름으로 Detector 를 만든다. LLM judge 는 judge_client(Adapter)를 주입받는다."""
    factory = _resolve("detector", name, DETECTORS)
    return factory(judge_client=judge_client, **params)


def get_adapter(name: str) -> Callable:
    """이름으로 Adapter 팩토리(클래스)를 돌려준다. 구성은 runner 가 한다."""
    return _resolve("adapter", name, ADAPTERS)


def available() -> dict[str, tuple[str, ...]]:
    """역할별 사용 가능한 이름 목록."""
    return {
        "probe": tuple(sorted(PROBES)),
        "detector": tuple(sorted(DETECTORS)),
        "adapter": tuple(sorted(ADAPTERS)),
    }
