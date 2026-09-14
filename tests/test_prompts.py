"""vendor.prompts — 벤더링 프롬프트의 무결성(checksum)·verbatim 특징·렌더 라운드트립."""
# ruff: noqa: E501  (벤더 파일 sha256 상수는 64자라 줄바꿈 불가)

import hashlib
from importlib.resources import files

import pytest

from redteam.vendor import prompts

# 각 벤더 파일의 sha256 (vendoring 시점에 고정 — PROVENANCE.md 와 일치)
CHECKSUMS = {
    "pair/roleplaying.txt": "aaf1642cd24a07afd13df970252ccf1eee387240cee202bd0af586bafa030b99",
    "pair/logical_appeal.txt": "96c861418874c2064eb636758c08718a531f301801a5310002f72c8086a37539",
    "pair/authority_endorsement.txt": "33034661741af82b7283f4a6ca8b2334a2c51602716cf54db56c4f21bbc6fbd9",
    "pair/judge_system.txt": "9be96058a93c83658c571dad93ae29d7c96b3f06c92a4ecbf1542cac0670b8aa",
    "pair/init_msg.txt": "6cc3b298c6702eb049724d03eb64d5e8184b10a9e3c319e858ac91bad864bb06",
    "pair/process_target_response.txt": "d1d8b2449163433b1ff54016d9a6fb23b22c8b267e3866d31fa2c84d14ac4294",
    "crescendo/crescendo_variant_1.yaml": "f522d7fb3394883cf6ad8ebb40b79110b5457f223998d5c0542dd3ec539bb4bf",
    "crescendo/refusal_default.yaml": "f398b1a77e526bd26b3ed2e731a1c7fbf19aada47ce889b9e9f52b55fba1eb2f",
    "crescendo/refusal_strict.yaml": "41bd1da6bb24aaa31058972dbaf469097b45c64b73eca683f0b151262a4e50ea",
    "crescendo/task_achieved_scale.yaml": "3e52aea1d3ba4539b813e0e401facf3f98464e15d042a0960dcaf48999c395d2",
    "crescendo/red_teamer_system_prompt.yaml": "74faaa76dcf507d3fe0741ff5adc75abb4b37ec0b1ce9e19c861cf16e81e2d22",
}


@pytest.mark.parametrize("rel,expected", CHECKSUMS.items())
def test_vendored_file_checksum(rel, expected):
    data = files("redteam.vendor").joinpath(rel).read_bytes()
    assert hashlib.sha256(data).hexdigest() == expected, f"{rel} 가 원본 바이트와 다름"


def _txt(rel):
    return files("redteam.vendor").joinpath(rel).read_text(encoding="utf-8")


class TestVerbatimFeatures:
    def test_judge_has_emdash(self):
        # "non-jailbroken response—either" 의 em-dash(U+2014) 보존
        assert "—" in _txt("pair/judge_system.txt")

    def test_roleplaying_trailing_space(self):
        # load-bearing 후행 공백("SETTING: " 뒤 개행) 보존
        assert "SETTING: \n" in _txt("pair/roleplaying.txt")

    def test_pair_placeholders_present(self):
        t = _txt("pair/roleplaying.txt")
        assert "{goal}" in t and "{target_str}" in t
        assert "{{" in t  # JSON 예시의 리터럴 중괄호는 이스케이프 상태

    def test_crescendo_jinja_placeholders_present(self):
        t = _txt("crescendo/crescendo_variant_1.yaml")
        assert "{{objective}}" in t and "{{max_turns}}" in t

    def test_crescendo_pinned_schema_key(self):
        t = _txt("crescendo/crescendo_variant_1.yaml")
        assert "generated_question" in t
        assert "next_message" not in t  # 고정 커밋(구 스키마)


class TestPairRender:
    def test_attacker_system_fills_and_no_residual(self):
        out = prompts.pair_attacker_system("roleplaying", "MYGOAL", "MYTARGET")
        assert "MYGOAL" in out and "MYTARGET" in out
        assert "{goal}" not in out and "{target_str}" not in out
        assert "{{" not in out  # 이스케이프가 단일 중괄호로 풀림
        assert '"improvement":' in out  # JSON 예시 유지

    def test_all_three_strategies(self):
        for s in prompts.PAIR_STRATEGIES:
            out = prompts.pair_attacker_system(s, "G", "T")
            assert "G" in out and "red teaming assistant" in out

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError):
            prompts.pair_attacker_system("nope", "G", "T")

    def test_judge_system(self):
        out = prompts.pair_judge_system("MYGOAL")
        assert "MYGOAL" in out and "Rating: [[rating]]" in out
        assert "{goal}" not in out

    def test_judge_user(self):
        assert prompts.pair_judge_user("P", "R") == "[PROMPT]:P\n[ASSISTANT'S RESPONSE]: R"

    def test_init_msg(self):
        out = prompts.pair_init_msg("G", "T")
        assert "G" in out and "T" in out and out.endswith("Begin.")
        assert "{goal}" not in out and "{target}" not in out

    def test_process_response(self):
        out = prompts.pair_process_response("RESP", 5, "G")
        assert out.startswith("LANGUAGE MODEL OUTPUT: RESP")
        assert "SCORE: 5" in out and "G" in out and "\n" in out


class TestCrescendoRender:
    def test_system_fills(self):
        out = prompts.crescendo_system("OBJ", 9)
        assert "OBJ" in out and "9" in out
        assert "{{objective}}" not in out and "{{max_turns}}" not in out
        assert "Prior Conversation Context" not in out  # context 없음 → if 블록 skip

    def test_system_with_context(self):
        out = prompts.crescendo_system("OBJ", 9, conversation_context="PRIORCTX")
        assert "PRIORCTX" in out and "Prior Conversation Context" in out

    def test_refusal_default_vs_strict(self):
        d = prompts.crescendo_refusal_system(False)
        s = prompts.crescendo_refusal_system(True)
        assert "score_value" in d and "refusal" in d.lower()
        assert "**Important**" in s and "safe completions" in s
        assert "**Important**" not in d

    def test_refusal_user(self):
        assert (
            prompts.crescendo_refusal_user("O", "R")
            == "conversation_objective: O\nresponse_to_evaluate_input: R"
        )

    def test_scale_system_fills_scale_args(self):
        out = prompts.crescendo_scale_system()
        assert "0" in out and "100" in out and "stop sign" in out
        assert "{{ examples }}" not in out and "{{ minimum_value }}" not in out

    def test_scale_user(self):
        assert prompts.crescendo_scale_user("O", "R") == "objective: O\nresponse: R"
