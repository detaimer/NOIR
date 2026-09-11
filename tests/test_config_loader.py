"""config_loader — yaml 읽기 + CLI 오버라이드 + from_dict + api_key_env 해석."""

from __future__ import annotations

import pytest

cl = pytest.importorskip("redteam.config_loader")
from redteam.core import ConfigError, EndpointConfig, RunConfig  # noqa: E402

YAML = """
target: {base_url: "http://t", model: "tm", api_key_env: "T_KEY"}
judge: {base_url: "http://j", model: "jm", api_key_env: "J_KEY"}
detectors: [refusal_match]
techniques: [flip_attack]
behaviors: builtin
budget: {target_calls: 7}
reporting: {html: false}
"""


def _write(tmp_path, text: str) -> str:
    p = tmp_path / "run.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_load_config_returns_cfg_and_raw(tmp_path):
    cfg, raw = cl.load_config(_write(tmp_path, YAML))
    assert isinstance(cfg, RunConfig)
    assert cfg.budget == 7
    assert cfg.target.model == "tm"
    assert cfg.techniques == ("flip_attack",)
    assert raw["target"]["model"] == "tm"  # 스냅샷용 원본 dict


def test_overrides_dotted_keys(tmp_path):
    cfg, raw = cl.load_config(
        _write(tmp_path, YAML),
        overrides={"budget.target_calls": 99, "target.model": "override"},
    )
    assert cfg.budget == 99
    assert cfg.target.model == "override"
    assert raw["budget"]["target_calls"] == 99


def test_resolve_api_key_from_env(monkeypatch):
    monkeypatch.setenv("T_KEY", "secret-123")
    ep = EndpointConfig(base_url="x", model="y", api_key_env="T_KEY")
    assert cl.resolve_api_key(ep) == "secret-123"


def test_resolve_api_key_none_when_no_env_name():
    ep = EndpointConfig(base_url="x", model="y", api_key_env=None)
    assert cl.resolve_api_key(ep) is None


def test_resolve_api_key_missing_env_raises(monkeypatch):
    monkeypatch.delenv("MISSING_KEY", raising=False)
    ep = EndpointConfig(base_url="x", model="y", api_key_env="MISSING_KEY")
    with pytest.raises(ConfigError):
        cl.resolve_api_key(ep)


def test_self_judge_yaml_raises(tmp_path):
    y = YAML.replace(
        'judge: {base_url: "http://j", model: "jm", api_key_env: "J_KEY"}',
        'judge: {base_url: "http://t", model: "tm"}',
    )
    with pytest.raises(ConfigError):
        cl.load_config(_write(tmp_path, y))


def test_self_judge_allowed_with_flag(tmp_path):
    y = YAML.replace(
        'judge: {base_url: "http://j", model: "jm", api_key_env: "J_KEY"}',
        'judge: {base_url: "http://t", model: "tm"}',
    )
    cfg, _ = cl.load_config(_write(tmp_path, y), allow_self_judge=True)
    assert cfg.allow_self_judge is True
