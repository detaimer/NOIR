"""vendor — 원저자 verbatim 프롬프트 자산 + 로더/파서 (probes·detectors 가 재사용).

역할 패키지가 아니며 core 처럼 최하위에 위치(레이어 게이트상 probes·detectors 가 import 가능).
원문·출처·라이선스는 vendor/NOTICE 와 vendor/*/PROVENANCE.md 참조.
"""

from redteam.vendor.parsing import (
    extract_crescendo_question,
    extract_pair_json,
    parse_pair_rating,
    parse_refusal,
    parse_scale,
    parse_scale_rationale,
)
from redteam.vendor.prompts import (
    PAIR_STRATEGIES,
    crescendo_refusal_system,
    crescendo_refusal_user,
    crescendo_scale_system,
    crescendo_scale_user,
    crescendo_system,
    pair_attacker_system,
    pair_init_msg,
    pair_judge_system,
    pair_judge_user,
    pair_process_response,
)

__all__ = [
    "extract_pair_json",
    "extract_crescendo_question",
    "parse_pair_rating",
    "parse_refusal",
    "parse_scale",
    "parse_scale_rationale",
    "PAIR_STRATEGIES",
    "pair_attacker_system",
    "pair_judge_system",
    "pair_judge_user",
    "pair_init_msg",
    "pair_process_response",
    "crescendo_system",
    "crescendo_refusal_system",
    "crescendo_refusal_user",
    "crescendo_scale_system",
    "crescendo_scale_user",
]
