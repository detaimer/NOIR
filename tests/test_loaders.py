"""behaviors.loaders — builtin + <path>.jsonl 디스패치, domain/limit 필터, unknown→ConfigError."""

from __future__ import annotations

import json
from pathlib import Path

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
        loaders.load_behaviors(BehaviorSpec(source="nope"))


# --- M13: jbb / HarmBench 로더 (로컬 파일만 — 네트워크 다운로드 없음) ---

FIXTURES = Path(__file__).parent / "fixtures"
JBB_CSV = FIXTURES / "jbb_sample.csv"
HARMBENCH_CSV = FIXTURES / "harmbench_sample.csv"


def _by_id(behaviors):
    return {b.id: b for b in behaviors}


def test_jbb_requires_local_path():
    """네트워크 다운로드를 하지 않으므로 path 가 없으면 안내와 함께 거부."""
    with pytest.raises(ConfigError, match="path"):
        loaders.load_behaviors(BehaviorSpec(source="jbb"))


def test_harmbench_requires_local_path():
    with pytest.raises(ConfigError, match="path"):
        loaders.load_behaviors(BehaviorSpec(source="harmbench"))


def test_missing_file_raises():
    with pytest.raises(ConfigError):
        loaders.load_behaviors(BehaviorSpec(source="jbb", path="/nonexistent/jbb.csv"))


def test_jbb_parses_rows():
    out = loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(JBB_CSV)))
    assert len(out) == 3
    assert all(b.source == "jbb" for b in out)
    b = _by_id(out)["jbb_1"]
    assert b.prompt.startswith("Develop malware")
    assert b.subcat == "Disable antivirus"


def test_jbb_maps_category_to_domain():
    out = _by_id(loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(JBB_CSV))))
    assert out["jbb_1"].domain == "cyber"  # Malware/Hacking → 내부 도메인
    assert out["jbb_2"].domain == "privacy"
    # 대응 도메인이 없는 카테고리는 슬러그로 보존(정보 손실 방지)
    assert out["jbb_0"].domain == "harassment_discrimination"


def test_jbb_preserves_original_taxonomy_as_tags():
    out = _by_id(loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(JBB_CSV))))
    assert "jbb:category:Malware/Hacking" in out["jbb_1"].tags
    assert "jbb:source:AdvBench" in out["jbb_1"].tags
    assert "jbb:category:Privacy" in out["jbb_2"].tags


def test_harmbench_parses_rows():
    out = loaders.load_behaviors(BehaviorSpec(source="harmbench", path=str(HARMBENCH_CSV)))
    assert len(out) == 3
    assert all(b.source == "harmbench" for b in out)
    b = _by_id(out)["hacking_atm_machine"]  # BehaviorID 를 id 로 사용
    assert b.prompt.startswith("Give detailed instructions")
    assert b.subcat == "cybercrime_intrusion"


def test_harmbench_maps_semantic_category_to_domain():
    out = _by_id(loaders.load_behaviors(BehaviorSpec(source="harmbench", path=str(HARMBENCH_CSV))))
    assert out["hacking_atm_machine"].domain == "cyber"
    assert out["chemical_warfare_agent_reaction"].domain == "cbrn"
    assert out["persuasive_article_election"].domain == "misinfo"


def test_harmbench_preserves_tags_and_categories():
    out = _by_id(loaders.load_behaviors(BehaviorSpec(source="harmbench", path=str(HARMBENCH_CSV))))
    b = out["persuasive_article_election"]
    assert "harmbench:functional:standard" in b.tags
    assert "harmbench:semantic:misinformation_disinformation" in b.tags
    assert "harmbench:tag:hash_check" in b.tags
    # Tags 가 빈 칸이면 tag 항목을 만들지 않는다
    assert not any(t.startswith("harmbench:tag:") for t in out["hacking_atm_machine"].tags)


def test_harmbench_contextual_behavior_embeds_context():
    """contextual behavior 는 ContextString 이 프롬프트의 일부 — 빠지면 과제가 성립하지 않는다."""
    out = _by_id(loaders.load_behaviors(BehaviorSpec(source="harmbench", path=str(HARMBENCH_CSV))))
    b = out["chemical_warfare_agent_reaction"]
    assert "A reaction of X with Y under reflux yields compound Z." in b.prompt
    assert "Determine what chemical warfare agent" in b.prompt
    assert "harmbench:functional:contextual" in b.tags


def test_external_sources_respect_domain_and_limit_filters():
    spec = BehaviorSpec(source="jbb", path=str(JBB_CSV), domain="cyber")
    out = loaders.load_behaviors(spec)
    assert [b.id for b in out] == ["jbb_1"]

    spec = BehaviorSpec(source="harmbench", path=str(HARMBENCH_CSV), limit=2)
    assert len(loaders.load_behaviors(spec)) == 2


def test_jbb_accepts_json_rows(tmp_path):
    """일부 배포본은 CSV 대신 JSON — 같은 컬럼이면 동일하게 파싱된다."""
    path = tmp_path / "jbb.json"
    path.write_text(
        json.dumps(
            [
                {
                    "Index": 7,
                    "Goal": "g",
                    "Behavior": "b",
                    "Category": "Privacy",
                    "Source": "Original",
                }
            ]
        ),
        encoding="utf-8",
    )
    out = loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(path)))
    assert out[0].id == "jbb_7"
    assert out[0].domain == "privacy"


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("Index,Category\n0,Privacy\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(path)))


def test_json_object_without_rows_raises_with_keys(tmp_path):
    """dict 인데 행 배열을 못 찾으면 조용히 0건이 되지 않고, 실제 최상위 키를 알려준다."""
    path = tmp_path / "jbb.json"
    path.write_text(
        json.dumps({"items": [{"Goal": "g", "Category": "Privacy"}], "meta": 1}), encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="items"):
        loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(path)))


@pytest.mark.parametrize("key", ["data", "rows", "behaviors"])
def test_json_object_row_array_keys(tmp_path, key):
    """배포본마다 감싸는 키가 다르다 — 흔한 이름 세 가지를 받아들인다."""
    path = tmp_path / "jbb.json"
    path.write_text(
        json.dumps({key: [{"Index": 3, "Goal": "g", "Category": "Privacy"}]}), encoding="utf-8"
    )
    assert [b.id for b in loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(path)))] == [
        "jbb_3"
    ]


def test_empty_file_raises(tmp_path):
    """헤더만 있는 CSV 도 0건 — 시도 0건짜리 리포트가 나오기 전에 막는다."""
    path = tmp_path / "empty.csv"
    path.write_text("Index,Goal,Category\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="행이 없습니다"):
        loaders.load_behaviors(BehaviorSpec(source="jbb", path=str(path)))


def test_empty_json_list_raises(tmp_path):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ConfigError, match="행이 없습니다"):
        loaders.load_behaviors(BehaviorSpec(source="harmbench", path=str(path)))


def test_domain_filter_yielding_zero_is_not_an_error():
    """파일은 정상인데 필터가 0건인 것은 오류가 아니다 (빈 리스트 반환)."""
    spec = BehaviorSpec(source="jbb", path=str(JBB_CSV), domain="nonexistent_domain")
    assert loaders.load_behaviors(spec) == []
