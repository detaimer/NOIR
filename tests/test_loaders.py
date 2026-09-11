"""behaviors.loaders — builtin + <path>.jsonl 디스패치, domain/limit 필터, unknown→ConfigError."""

from __future__ import annotations

import json

import pytest

loaders = pytest.importorskip("redteam.behaviors.loaders")
from redteam.core import BehaviorSpec, ConfigError  # noqa: E402


def test_load_builtin():
    out = loaders.load_behaviors(BehaviorSpec(source="builtin"))
    assert len(out) >= 12
    assert all(b.source == "builtin" for b in out)


def test_load_builtin_with_domain_filter():
    out = loaders.load_behaviors(BehaviorSpec(source="builtin", domain="ot_ics"))
    assert out
    assert all(b.domain == "ot_ics" for b in out)


def test_load_builtin_with_limit():
    out = loaders.load_behaviors(BehaviorSpec(source="builtin", limit=3))
    assert len(out) == 3


def test_load_jsonl_file(tmp_path):
    path = tmp_path / "seeds.jsonl"
    rows = [
        {"id": "x1", "prompt": "p1", "domain": "cyber", "tags": ["owasp-llm:LLM01"]},
        {
            "id": "x2",
            "prompt": "p2",
            "domain": "privacy",
            "subcat": "pii",
            "tags": ["owasp-llm:LLM06"],
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    out = loaders.load_behaviors(BehaviorSpec(source=str(path)))
    assert len(out) == 2
    assert out[0].id == "x1"
    assert out[0].tags == ("owasp-llm:LLM01",)  # 태그 보존 + tuple 화
    assert out[1].subcat == "pii"


def test_jsonl_domain_and_limit_filter(tmp_path):
    path = tmp_path / "seeds.jsonl"
    rows = [
        {"id": "a", "prompt": "p", "domain": "cyber"},
        {"id": "b", "prompt": "p", "domain": "ot_ics"},
        {"id": "c", "prompt": "p", "domain": "ot_ics"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")

    out = loaders.load_behaviors(BehaviorSpec(source=str(path), domain="ot_ics", limit=1))
    assert len(out) == 1
    assert out[0].domain == "ot_ics"


def test_unknown_source_raises():
    with pytest.raises(ConfigError):
        loaders.load_behaviors(BehaviorSpec(source="jbb"))
    with pytest.raises(ConfigError):
        loaders.load_behaviors(BehaviorSpec(source="harmbench"))
