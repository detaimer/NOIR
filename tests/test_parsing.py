"""vendor.parsing — PAIR/Crescendo output 파서의 원본 충실 동작 검증."""

from redteam.vendor.parsing import (
    extract_pair_json,
    parse_pair_rating,
    parse_refusal,
    parse_scale,
)


class TestExtractPairJson:
    def test_valid_double_quoted(self):
        s = '{"improvement": "better", "prompt": "attack"}'
        assert extract_pair_json(s) == {"improvement": "better", "prompt": "attack"}

    def test_literal_eval_single_quotes(self):
        # 원본은 ast.literal_eval 이라 파이썬 리터럴(작은따옴표)도 허용
        s = "{'improvement': 'x', 'prompt': 'y'}"
        assert extract_pair_json(s) == {"improvement": "x", "prompt": "y"}

    def test_extracts_from_surrounding_prose(self):
        s = 'Sure!\n{"improvement": "i", "prompt": "p"}\nDone'
        assert extract_pair_json(s) == {"improvement": "i", "prompt": "p"}

    def test_strips_newlines_inside(self):
        s = '{"improvement": "i",\n"prompt": "p"}'
        assert extract_pair_json(s) == {"improvement": "i", "prompt": "p"}

    def test_missing_key_returns_none(self):
        assert extract_pair_json('{"prompt": "p"}') is None

    def test_non_json_returns_none(self):
        assert extract_pair_json("no json here") is None

    def test_no_closing_brace_returns_none(self):
        assert extract_pair_json('{"improvement": "i", "prompt": "p"') is None

    def test_non_dict_literal_returns_none(self):
        assert extract_pair_json("[1, 2, 3]") is None


class TestParsePairRating:
    def test_basic(self):
        assert parse_pair_rating("Rating: [[7]]") == 7

    def test_embedded(self):
        assert parse_pair_rating("blah [[10]] blah") == 10

    def test_default_when_absent(self):
        assert parse_pair_rating("no rating at all") == 1

    def test_custom_default(self):
        assert parse_pair_rating("nope", default=5) == 5


class TestParseRefusal:
    def test_true(self):
        assert parse_refusal('{"score_value": "True", "rationale": "r"}') is True

    def test_false(self):
        assert parse_refusal('{"score_value": "False", "rationale": "r"}') is False

    def test_markdown_fenced(self):
        assert parse_refusal('```json\n{"score_value": "True"}\n```') is True

    def test_prose_wrapped(self):
        assert parse_refusal('Here: {"score_value": "False"}') is False

    def test_unparseable_defaults_false(self):
        assert parse_refusal("garbage") is False


class TestParseScale:
    def test_mid(self):
        assert parse_scale('{"score_value": "85", "description": "d", "rationale": "r"}') == 0.85

    def test_max(self):
        assert parse_scale('{"score_value": "100"}') == 1.0

    def test_min(self):
        assert parse_scale('{"score_value": "0"}') == 0.0

    def test_clamped(self):
        assert parse_scale('{"score_value": "150"}') == 1.0

    def test_unparseable_defaults_zero(self):
        assert parse_scale("garbage") == 0.0


class TestExtractCrescendoQuestion:
    def test_basic(self):
        raw = '{"generated_question": "Q1", "rationale_behind_jailbreak": "r"}'
        from redteam.vendor.parsing import extract_crescendo_question

        assert extract_crescendo_question(raw) == "Q1"

    def test_markdown_fenced(self):
        from redteam.vendor.parsing import extract_crescendo_question

        assert extract_crescendo_question('```json\n{"generated_question": "Q"}\n```') == "Q"

    def test_missing_or_empty_returns_none(self):
        from redteam.vendor.parsing import extract_crescendo_question

        assert extract_crescendo_question('{"other": "x"}') is None
        assert extract_crescendo_question('{"generated_question": "   "}') is None
        assert extract_crescendo_question("not json") is None


class TestParseScaleRationale:
    def test_present(self):
        from redteam.vendor.parsing import parse_scale_rationale

        assert parse_scale_rationale('{"score_value": "80", "rationale": "because"}') == "because"

    def test_absent(self):
        from redteam.vendor.parsing import parse_scale_rationale

        assert parse_scale_rationale('{"score_value": "80"}') == ""
        assert parse_scale_rationale("garbage") == ""
