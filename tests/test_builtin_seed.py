"""behaviors.builtin_seed — 내장 시드 팩의 불변식(개수·유일성·태그·taxonomy)."""

from __future__ import annotations

import pytest

seed = pytest.importorskip("redteam.behaviors.builtin_seed")


def test_returns_fresh_list():
    a = seed.builtin_behaviors()
    b = seed.builtin_behaviors()
    assert a is not b  # 매 호출 새 리스트
    assert a == b


def test_count_in_range():
    behaviors = seed.builtin_behaviors()
    assert 12 <= len(behaviors) <= 16


def test_ids_unique():
    behaviors = seed.builtin_behaviors()
    ids = [b.id for b in behaviors]
    assert len(ids) == len(set(ids))


def test_all_have_domain_and_tags():
    for b in seed.builtin_behaviors():
        assert b.domain, f"{b.id} 에 domain 누락"
        assert b.tags, f"{b.id} 에 tags 누락"
        assert b.subcat, f"{b.id} 에 subcat 누락"
        assert b.prompt


def test_has_ot_ics_with_attack_ics_tag():
    behaviors = seed.builtin_behaviors()
    ot = [b for b in behaviors if b.domain == "ot_ics"]
    assert ot, "ot_ics 도메인 behavior 가 최소 1개 있어야 함"
    assert any(t.startswith("attack-ics:") for b in ot for t in b.tags)


def test_multiple_taxonomy_prefixes_present():
    prefixes = {t.split(":", 1)[0] for b in seed.builtin_behaviors() for t in b.tags if ":" in t}
    # owasp-llm / attack / attack-ics / atlas 등 최소 3종
    assert len(prefixes) >= 3, f"taxonomy 다양성 부족: {prefixes}"


def test_multiple_domains_covered():
    domains = {b.domain for b in seed.builtin_behaviors()}
    assert len(domains) >= 4
