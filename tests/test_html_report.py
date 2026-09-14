"""HTML 리포트 렌더 검증 — 8섹션·히트맵·드릴다운·자기완결성(오프라인)."""

from __future__ import annotations

import pytest

pytest.importorskip("redteam.reporting.html_report")

from redteam.core import Attempt, Behavior, DetectionResult, Turn  # noqa: E402
from redteam.reporting.aggregate import summarize  # noqa: E402
from redteam.reporting.html_report import SECTIONS, render_html, write_html  # noqa: E402


def _dr(success: bool, name: str, score=None, categories=(), rationale=None) -> DetectionResult:
    return DetectionResult(
        success=success,
        judge_name=name,
        score=score,
        categories=tuple(categories),
        rationale=rationale,
    )


def _attempt(behavior_id, technique, success, target_calls, detections, turns=None) -> Attempt:
    turns = turns or (Turn(prompt="prompt-1", response="response-1"),)
    return Attempt(
        behavior_id=behavior_id,
        technique=technique,
        turns=turns,
        final_prompt=turns[-1].prompt,
        final_response=turns[-1].response,
        detections=detections,
        success=success,
        target_calls=target_calls,
    )


@pytest.fixture
def behaviors() -> list[Behavior]:
    return [
        Behavior(
            id="b1",
            prompt="샘플 유해요청 1",
            domain="cyber",
            subcat="malware",
            tags=("owasp-llm:LLM01",),
        ),
        Behavior(
            id="b2",
            prompt="샘플 유해요청 2",
            domain="ot_ics",
            subcat="plc",
            tags=("attack-ics:T0836",),
        ),
    ]


@pytest.fixture
def attempts() -> list[Attempt]:
    return [
        _attempt(
            "b1",
            "flip_attack",
            True,
            1,
            (
                _dr(True, "refusal_match"),
                _dr(True, "llama_guard", None, ("S9",)),
                _dr(True, "strong_reject", 0.75, ("cyber",), rationale="구체적 절차를 제공"),
            ),
        ),
        _attempt(
            "b2",
            "crescendo",
            False,
            3,
            (_dr(False, "refusal_match"),),
            turns=(
                Turn(prompt="turn-a-prompt", response="turn-a-response"),
                Turn(prompt="turn-b-prompt", response="turn-b-response"),
            ),
        ),
    ]


@pytest.fixture
def html(attempts, behaviors) -> str:
    return render_html(
        summarize(attempts, behaviors),
        attempts,
        behaviors=behaviors,
        meta={"target": "local/deepseek-r1", "budget": 50, "timestamp": "20260914-101500"},
    )


# --- 기본 형태 ---


def test_returns_html_document(html):
    assert html.lstrip().lower().startswith("<!doctype html")
    assert "</html>" in html


def test_declares_eight_sections(html):
    assert len(SECTIONS) == 8
    for title in SECTIONS:
        assert title in html, f"섹션 누락: {title}"


def test_self_contained_no_external_assets(html):
    """오프라인에서 파일 하나로 열려야 한다 — 외부 CDN/링크 참조 금지."""
    assert "<style>" in html
    assert 'src="http' not in html
    assert 'href="http' not in html


# --- 섹션 내용 ---


def test_headline_shows_overall_and_meta(html):
    assert "50.0%" in html  # overall ASR = 1/2
    assert "local/deepseek-r1" in html
    assert "50" in html  # budget
    assert "20260914-101500" in html


def test_technique_table_has_fair_asr_columns(html):
    for col in ("ASR@B", "avg_calls", "efficiency", "SR_avg"):
        assert col in html
    assert "flip_attack" in html
    assert "crescendo" in html


def test_heatmap_cells_carry_asr_and_intensity(html):
    """히트맵 셀은 ASR 값(data-asr)과 위험도 등급(data-risk)을 함께 싣는다."""
    assert 'data-asr="1.00"' in html  # cyber × flip_attack
    assert 'data-asr="0.00"' in html  # ot_ics × crescendo
    assert "data-risk=" in html
    assert "cyber" in html and "ot_ics" in html


def test_heatmap_marks_unmeasured_cells(html):
    """시도가 없는 (도메인, 기법) 조합은 0% 가 아니라 '미측정' 으로 구분 표기."""
    assert "cell-empty" in html


def test_top3_and_category_and_taxonomy(html):
    assert "ot_ics" in html
    assert "S9" in html  # 카테고리 분포
    assert "owasp-llm:LLM01" in html  # taxonomy 커버리지
    assert "attack-ics:T0836" in html


def test_judge_agreement_section_lists_each_judge(html):
    for judge in ("refusal_match", "llama_guard", "strong_reject"):
        assert judge in html
    assert "100.0%" in html  # judge_agreement = 1.0


def test_drilldown_has_transcript_and_judge_details(html):
    assert "<details" in html
    # 멀티턴 transcript 가 턴 단위로 모두 실린다
    for frag in ("turn-a-prompt", "turn-a-response", "turn-b-prompt", "turn-b-response"):
        assert frag in html
    # judge 3종의 점수·근거
    assert "0.75" in html
    assert "구체적 절차를 제공" in html
    # behavior 메타
    assert "샘플 유해요청 1" in html
    assert "malware" in html


# --- 안전성·견고성 ---


def test_escapes_untrusted_content(behaviors):
    """타깃 응답은 신뢰할 수 없는 텍스트 — 반드시 이스케이프."""
    evil = "<script>alert('xss')</script>"
    a = _attempt(
        "b1",
        "flip_attack",
        True,
        1,
        (_dr(True, "refusal_match"),),
        turns=(Turn(prompt="p", response=evil),),
    )
    out = render_html(summarize([a], behaviors), [a], behaviors=behaviors)
    assert "<script>alert" not in out
    assert "&lt;script&gt;" in out


def test_renders_with_empty_attempts():
    out = render_html(summarize([], None), [], behaviors=None)
    assert out.lstrip().lower().startswith("<!doctype html")
    for title in SECTIONS:
        assert title in out


def test_renders_without_behaviors_or_meta(attempts):
    out = render_html(summarize(attempts, None), attempts)
    assert "unknown" in out  # behavior 미상 → unknown 도메인


def test_binary_judge_score_renders_as_na(html):
    """이진 judge 는 score=None — 'N/A' 로 렌더(숫자 포맷 크래시 없음)."""
    assert "N/A" in html


# --- 파일 쓰기 ---


def test_write_html_creates_report_file(tmp_path, attempts, behaviors):
    path = write_html(tmp_path / "run", summarize(attempts, behaviors), attempts, behaviors)
    assert path.name == "report.html"
    assert path.exists()
    assert path.read_text(encoding="utf-8").lstrip().lower().startswith("<!doctype html")


def test_write_html_creates_parent_dirs(tmp_path, attempts, behaviors):
    path = write_html(tmp_path / "a" / "b", summarize(attempts, behaviors), attempts, behaviors)
    assert path.parent.is_dir()
