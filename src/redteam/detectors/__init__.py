"""detectors — 성공 판정(judge) 컴포넌트와 이름 조회용 레지스트리.

레지스트리 규약: 각 값은 팩토리 `(judge_client: Adapter | None = None, **params) -> Detector`.
무모델 judge(RefusalMatch)는 judge_client 를 무시하고, LLM judge 는 이를 클라이언트로 주입받는다.
pair_judge/crescendo_* 는 원저자 프롬프트를 재사용하는 기법 고유 judge(vendor/ 참조).
"""

from __future__ import annotations

from redteam.detectors.crescendo_objective import CrescendoObjective
from redteam.detectors.crescendo_refusal import CrescendoRefusal
from redteam.detectors.llama_guard import LlamaGuard
from redteam.detectors.pair_judge import PairJudge
from redteam.detectors.refusal_match import RefusalMatch
from redteam.detectors.strong_reject import StrongReject

DETECTORS = {
    "refusal_match": lambda judge_client=None, **p: RefusalMatch(**p),
    "llama_guard": lambda judge_client=None, **p: LlamaGuard(judge_client, **p),
    "strong_reject": lambda judge_client=None, **p: StrongReject(judge_client, **p),
    "pair_judge": lambda judge_client=None, **p: PairJudge(judge_client, **p),
    "crescendo_refusal": lambda judge_client=None, **p: CrescendoRefusal(judge_client, **p),
    "crescendo_objective": lambda judge_client=None, **p: CrescendoObjective(judge_client, **p),
}

__all__ = [
    "DETECTORS",
    "LlamaGuard",
    "RefusalMatch",
    "StrongReject",
    "PairJudge",
    "CrescendoRefusal",
    "CrescendoObjective",
]
