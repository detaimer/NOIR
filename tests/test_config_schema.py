"""core.config_schema — RunConfig.from_dict (순수 파싱 + target≠judge 검증)."""

from __future__ import annotations

import pytest

cs = pytest.importorskip("redteam.core.config_schema")
errs = pytest.importorskip("redteam.core.errors")


def _valid_dict():
    return {
        "target": {"base_url": "http://t", "model": "target-model", "api_key_env": "T_KEY"},
        "judge": {"base_url": "http://j", "model": "judge-model", "api_key_env": "J_KEY"},
        "attacker": {"base_url": "http://a", "model": "attacker-model"},
        "detectors": ["refusal_match", {"strong_reject": {"threshold": 0.5}}],
        "techniques": ["flip_attack", "pair"],
        "behaviors": {"source": "builtin", "domain": "ot_ics", "limit": 5},
        "budget": {"target_calls": 42},
        "reporting": {"html": True},
    }


def test_from_dict_builds_valid_config():
    cfg = cs.RunConfig.from_dict(_valid_dict())
    assert cfg.target.base_url == "http://t"
    assert cfg.target.model == "target-model"
    assert cfg.target.api_key_env == "T_KEY"
    assert cfg.judge is not None and cfg.judge.model == "judge-model"
    assert cfg.attacker is not None and cfg.attacker.api_key_env is None
    assert tuple(t.name for t in cfg.techniques) == ("flip_attack", "pair")
    assert cfg.budget == 42


def test_endpoint_adapter_defaults_and_override():
    d = _valid_dict()
    cfg = cs.RunConfig.from_dict(d)
    # 기본 어댑터는 http_openai
    assert cfg.target.adapter == "http_openai"
    # 명시하면 반영 (예: manual 타깃)
    d2 = _valid_dict()
    d2["target"] = {"base_url": "-", "model": "-", "adapter": "manual"}
    del d2["judge"]  # manual 타깃과 self-judge 검증 무관하게
    d2["detectors"] = ["refusal_match"]
    cfg2 = cs.RunConfig.from_dict(d2)
    assert cfg2.target.adapter == "manual"


def test_detectors_parse_string_and_dict_forms():
    cfg = cs.RunConfig.from_dict(_valid_dict())
    assert cfg.detectors[0].name == "refusal_match"
    assert cfg.detectors[0].params == {}
    assert cfg.detectors[1].name == "strong_reject"
    assert cfg.detectors[1].params == {"threshold": 0.5}


def test_behaviors_spec_fields():
    cfg = cs.RunConfig.from_dict(_valid_dict())
    assert cfg.behaviors.source == "builtin"
    assert cfg.behaviors.domain == "ot_ics"
    assert cfg.behaviors.limit == 5


def test_behaviors_accepts_bare_string_source():
    d = _valid_dict()
    d["behaviors"] = "harmbench"
    cfg = cs.RunConfig.from_dict(d)
    assert cfg.behaviors.source == "harmbench"
    assert cfg.behaviors.domain is None


def test_self_judge_same_endpoint_raises():
    d = _valid_dict()
    d["judge"] = dict(d["target"])  # 동일 base_url+model
    with pytest.raises(errs.ConfigError):
        cs.RunConfig.from_dict(d)


def test_self_judge_allowed_with_flag():
    d = _valid_dict()
    d["judge"] = dict(d["target"])
    cfg = cs.RunConfig.from_dict(d, allow_self_judge=True)
    assert cfg.allow_self_judge is True
    assert cfg.judge.identity() == cfg.target.identity()


def test_missing_target_raises():
    d = _valid_dict()
    del d["target"]
    with pytest.raises(errs.ConfigError):
        cs.RunConfig.from_dict(d)


def test_no_judge_endpoint_is_ok():
    d = _valid_dict()
    del d["judge"]
    d["detectors"] = ["refusal_match"]  # 엔드포인트 불필요 judge 만
    cfg = cs.RunConfig.from_dict(d)
    assert cfg.judge is None


def test_techniques_parse_string_and_dict_forms():
    d = _valid_dict()
    d["techniques"] = ["flip_attack", {"pair": {"n_streams": 3, "n_iterations": 2}}]
    cfg = cs.RunConfig.from_dict(d)
    assert cfg.techniques[0].name == "flip_attack"
    assert cfg.techniques[0].params == {}
    assert cfg.techniques[1].name == "pair"
    assert cfg.techniques[1].params == {"n_streams": 3, "n_iterations": 2}


def test_techniques_malformed_entry_raises():
    d = _valid_dict()
    d["techniques"] = [{"a": {}, "b": {}}]  # 단일 키가 아님
    with pytest.raises(errs.ConfigError):
        cs.RunConfig.from_dict(d)


def test_techniques_non_mapping_params_raises():
    d = _valid_dict()
    d["techniques"] = [{"pair": ["not", "a", "map"]}]
    with pytest.raises(errs.ConfigError):
        cs.RunConfig.from_dict(d)


# --- M13: 외부 behavior 셋(jbb/harmbench)의 로컬 파일 경로 ---


def test_behaviors_spec_carries_path():
    d = _valid_dict()
    d["behaviors"] = {"source": "harmbench", "path": "data/harmbench.csv", "limit": 10}
    cfg = cs.RunConfig.from_dict(d)
    assert cfg.behaviors.source == "harmbench"
    assert cfg.behaviors.path == "data/harmbench.csv"
    assert cfg.behaviors.limit == 10


def test_behaviors_path_defaults_to_none():
    assert cs.RunConfig.from_dict(_valid_dict()).behaviors.path is None


# --- 기법 param 검증 헬퍼 (probe 진입부에서 사용) ---


def test_require_positive_int_passes_through():
    assert cs.require_positive_int(3, name="pair.n_streams") == 3
    assert cs.require_positive_int("4", name="pair.n_streams") == 4


def test_require_positive_int_rejects_zero_and_negative():
    for bad in (0, -1):
        with pytest.raises(errs.ConfigError, match="1 이상"):
            cs.require_positive_int(bad, name="pair.n_iterations")


def test_require_positive_int_rejects_non_integer():
    for bad in ("x", None, 1.5):
        with pytest.raises(errs.ConfigError, match="정수"):
            cs.require_positive_int(bad, name="crescendo.max_turns")


def test_require_positive_int_message_names_the_setting():
    with pytest.raises(errs.ConfigError, match="crescendo.max_turns"):
        cs.require_positive_int(0, name="crescendo.max_turns")


def test_require_non_negative_int_allows_zero():
    assert cs.require_non_negative_int(0, name="crescendo.max_backtracks") == 0
    assert cs.require_non_negative_int("2", name="crescendo.max_backtracks") == 2


def test_require_non_negative_int_rejects_negative_and_non_integer():
    with pytest.raises(errs.ConfigError, match="0 이상"):
        cs.require_non_negative_int(-1, name="crescendo.max_backtracks")
    with pytest.raises(errs.ConfigError, match="정수"):
        cs.require_non_negative_int("x", name="crescendo.max_backtracks")


def test_bool_is_not_accepted_as_int():
    """YAML 의 `true` 가 1 로 조용히 통과하면 설정 오타를 놓친다."""
    with pytest.raises(errs.ConfigError, match="정수"):
        cs.require_positive_int(True, name="pair.n_streams")
