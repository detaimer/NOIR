"""CrescendoRefusal — 거부 판정·strict 프롬프트·user 포맷 검증 (mock judge_client)."""

from redteam.core import Behavior
from redteam.detectors.crescendo_refusal import CrescendoRefusal

BEH = Behavior(id="b1", prompt="do the objective", domain="cyber")


def test_refusal_means_not_success(fake_adapter):
    det = CrescendoRefusal(fake_adapter(responses='{"score_value": "True", "rationale": "r"}'))
    r = det.judge(BEH, "q", "I cannot help with that")
    assert r.success is False
    assert r.categories == ("refusal",)
    assert r.judge_name == "crescendo_refusal"


def test_non_refusal_is_success(fake_adapter):
    det = CrescendoRefusal(fake_adapter(responses='{"score_value": "False"}'))
    r = det.judge(BEH, "q", "Sure, here is ...")
    assert r.success is True
    assert r.categories == ()


def test_default_uses_default_refusal_prompt(fake_adapter):
    client = fake_adapter(responses='{"score_value": "False"}')
    CrescendoRefusal(client, strict=False).judge(BEH, "q", "resp")
    _, user, system = client.calls[0]
    assert user == "conversation_objective: do the objective\nresponse_to_evaluate_input: resp"
    assert "**Important**" not in system


def test_strict_uses_strict_prompt(fake_adapter):
    client = fake_adapter(responses='{"score_value": "True"}')
    CrescendoRefusal(client, strict=True).judge(BEH, "q", "resp")
    _, _, system = client.calls[0]
    assert "**Important**" in system and "safe completions" in system
