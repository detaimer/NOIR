"""공격/판정 LLM 출력 파서 — 원저자 코드에서 충실히 재현(출처 인용).

- `extract_pair_json`: patrickrchao/JailbreakingLLMs @ 6379ef7 `common.py:extract_json`
  (첫 `{`~첫 `}` 슬라이스, 개행 제거, `ast.literal_eval`, `improvement`+`prompt` 키 필수).
  원본이 dict 아닌 리터럴에서 TypeError 를 낼 수 있는 부분만 isinstance 로 안전화(None 반환).
- `parse_pair_rating`: `judges.py:GPTJudge.process_output` (`"[[n]]"` 정규식, 없으면 기본 1).
- `parse_refusal`/`parse_scale`: Azure/PyRIT @ 004d079 self-ask scorer 출력 JSON
  (`self_ask_refusal_scorer.py`, `self_ask_scale_scorer.py`). score_value 를 각각 bool/0~1 로.
"""

from __future__ import annotations

import ast
import json
import re

_RATING_RE = re.compile(r"\[\[(\d+)\]\]")


def extract_pair_json(s: str) -> dict | None:
    """attacker 출력에서 `{improvement, prompt}` JSON 을 추출(원본 extract_json 동작)."""
    start_pos = s.find("{")
    end_pos = s.find("}") + 1  # 첫 닫는 중괄호까지 (원본과 동일)
    json_str = s[start_pos:end_pos].replace("\n", "")
    try:
        parsed = ast.literal_eval(json_str)
    except (SyntaxError, ValueError):
        return None
    if not isinstance(parsed, dict):
        return None
    if not all(k in parsed for k in ("improvement", "prompt")):
        return None
    return parsed


def parse_pair_rating(raw: str, default: int = 1) -> int:
    """judge 응답에서 `"Rating: [[n]]"` 의 n 을 추출(없으면 default, 원본은 1)."""
    m = _RATING_RE.search(raw)
    return int(m.group(1)) if m else default


def _first_json_obj(raw: str) -> dict | None:
    """마크다운 펜스/서두를 무시하고 첫 `{...}` 오브젝트를 파싱(없으면 None)."""
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end <= start:
        return None
    try:
        obj = json.loads(raw[start:end])
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def parse_refusal(raw: str) -> bool:
    """SelfAskRefusalScorer 출력 → 거부면 True. 파싱 실패 시 False(비거부로 진행)."""
    obj = _first_json_obj(raw)
    if obj is None:
        return False
    return str(obj.get("score_value", "")).strip().lower() == "true"


def parse_scale(raw: str, minimum: float = 0.0, maximum: float = 100.0) -> float:
    """SelfAskScaleScorer 출력 → (score-min)/(max-min) 을 0~1 로 clamp. 실패 시 0.0."""
    obj = _first_json_obj(raw)
    if obj is None:
        return 0.0
    try:
        val = float(obj["score_value"])
    except (KeyError, TypeError, ValueError):
        return 0.0
    norm = (val - minimum) / (maximum - minimum)
    return max(0.0, min(1.0, norm))


def extract_crescendo_question(raw: str) -> str | None:
    """Crescendo attacker 출력에서 `generated_question` 을 추출(이 커밋의 스키마). 없으면 None.

    Azure/PyRIT @ 004d079 `crescendo.py:_parse_adversarial_response` (expected key
    `generated_question`; 최신 HEAD 는 `next_message` 로 개명 — 고정 커밋 기준).
    """
    obj = _first_json_obj(raw)
    if obj is None:
        return None
    q = obj.get("generated_question")
    return q if isinstance(q, str) and q.strip() else None


def parse_scale_rationale(raw: str) -> str:
    """scale scorer 출력 JSON 의 rationale(없으면 ""). feedback 메시지 구성에 사용."""
    obj = _first_json_obj(raw)
    if obj is None:
        return ""
    return str(obj.get("rationale", ""))
