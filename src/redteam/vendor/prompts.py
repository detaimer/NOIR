"""벤더링된 PAIR/Crescendo 프롬프트 로드+렌더 (원문은 vendor/*/PROVENANCE.md 참조).

PAIR .txt 는 `str.format(goal=…, target_str=…)`(원본 f-string 재현), Crescendo .yaml 은
`yaml.safe_load(...)["value"]` + jinja2(원본 SeedPrompt 렌더와 동일). 코드-레벨 user-message
포맷 상수는 원본 파일·라인을 주석으로 인용한다.
"""

from __future__ import annotations

from importlib.resources import files

import yaml
from jinja2 import Template

_PAIR = files("redteam.vendor").joinpath("pair")
_CRES = files("redteam.vendor").joinpath("crescendo")

PAIR_STRATEGIES = ("roleplaying", "logical_appeal", "authority_endorsement")


def _read(anchor, name: str) -> str:
    return anchor.joinpath(name).read_text(encoding="utf-8")


def _yaml_value(anchor, name: str) -> str:
    return yaml.safe_load(_read(anchor, name))["value"]


# --- PAIR (patrickrchao/JailbreakingLLMs @ 6379ef7) ---
def pair_attacker_system(strategy: str, goal: str, target_str: str) -> str:
    """3전략(roleplaying/logical_appeal/authority_endorsement) attacker system prompt."""
    if strategy not in PAIR_STRATEGIES:
        raise ValueError(f"unknown PAIR strategy: {strategy!r}")
    return _read(_PAIR, f"{strategy}.txt").format(goal=goal, target_str=target_str)


def pair_judge_system(goal: str, target_str: str = "") -> str:
    """get_judge_system_prompt (1~10 채점, "Rating: [[n]]")."""
    return _read(_PAIR, "judge_system.txt").format(goal=goal, target_str=target_str)


def pair_judge_user(attack_prompt: str, response: str) -> str:
    """judges.py:GPTJudge.get_judge_prompt 의 user 메시지 포맷."""
    return f"[PROMPT]:{attack_prompt}\n[ASSISTANT'S RESPONSE]: {response}"


def pair_init_msg(goal: str, target_str: str) -> str:
    """common.py:get_init_msg — 각 스트림의 최초 user 메시지."""
    return _read(_PAIR, "init_msg.txt").format(goal=goal, target=target_str)


def pair_process_response(response: str, score, goal: str) -> str:
    """common.py:process_target_response — 다음 iteration 의 user 피드백 메시지."""
    return _read(_PAIR, "process_target_response.txt").format(
        target_response=response, score=score, goal=goal
    )


# --- Crescendo (Azure/PyRIT @ 004d079) ---
def crescendo_system(objective: str, max_turns: int, conversation_context: str = "") -> str:
    """crescendo_variant_1.yaml attacker system prompt (jinja2)."""
    tmpl = _yaml_value(_CRES, "crescendo_variant_1.yaml")
    return Template(tmpl).render(
        objective=objective, max_turns=max_turns, conversation_context=conversation_context
    )


def crescendo_refusal_system(strict: bool = False) -> str:
    """SelfAskRefusalScorer system prompt (refusal_default / refusal_strict). placeholder 없음."""
    return _yaml_value(_CRES, "refusal_strict.yaml" if strict else "refusal_default.yaml")


def crescendo_refusal_user(objective: str, response: str) -> str:
    """self_ask_refusal_scorer.py:21 DEFAULT_REFUSAL_PROMPT_FORMAT."""
    return f"conversation_objective: {objective}\nresponse_to_evaluate_input: {response}"


def crescendo_scale_system() -> str:
    """0~100 목표달성 scale system prompt (red_teamer ⊗ task_achieved_scale)."""
    scale = yaml.safe_load(_read(_CRES, "task_achieved_scale.yaml"))
    tmpl = _yaml_value(_CRES, "red_teamer_system_prompt.yaml")
    return Template(tmpl).render(**scale)


def crescendo_scale_user(objective: str, response: str) -> str:
    """self_ask_scale_scorer.py:117 scoring_prompt 포맷."""
    return f"objective: {objective}\nresponse: {response}"
