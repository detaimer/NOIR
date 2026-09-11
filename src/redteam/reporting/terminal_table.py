"""터미널용 ASCII 요약표 렌더 — 순수(rich 미사용).

기법별 ASR@B·평균호출·efficiency·StrongREJECT평균 표 + 도메인/카테고리 섹션.
"""

from __future__ import annotations

from redteam.reporting.aggregate import Summary

_TECH_COLS = ("technique", "n", "ASR@B", "avg_calls", "efficiency", "SR_avg")
_TECH_WIDTHS = (20, 5, 7, 10, 11, 7)


def _fmt_row(values: tuple[str, ...], widths: tuple[int, ...]) -> str:
    """열을 폭에 맞춰 정렬(첫 열 좌측, 나머지 우측)해 ' | ' 로 연결."""
    cells = []
    for i, (val, w) in enumerate(zip(values, widths, strict=True)):
        cells.append(val.ljust(w) if i == 0 else val.rjust(w))
    return " | ".join(cells)


def _pct(x: float) -> str:
    return f"{x:.1%}"


def _num(x: float) -> str:
    return f"{x:.2f}"


def _technique_table(summary: Summary) -> list[str]:
    """기법별 지표 표 라인들."""
    lines = ["Per-technique (Fair-ASR @ budget B):"]
    header = _fmt_row(_TECH_COLS, _TECH_WIDTHS)
    lines.append(header)
    lines.append("-" * len(header))
    for tech, s in sorted(summary.per_technique.items(), key=lambda kv: (-kv[1]["asr"], kv[0])):
        lines.append(
            _fmt_row(
                (
                    tech,
                    str(s["n"]),
                    _pct(s["asr"]),
                    _num(s["avg_target_calls"]),
                    _num(s["efficiency"]),
                    _num(s["strong_reject_avg"]),
                ),
                _TECH_WIDTHS,
            )
        )
    return lines


def _domain_section(summary: Summary) -> list[str]:
    """도메인별 ASR 섹션."""
    lines = ["", "Per-domain (ASR):"]
    for dom, s in sorted(summary.per_domain.items(), key=lambda kv: (-kv[1]["asr"], kv[0])):
        lines.append(f"  {dom:<16} {_pct(s['asr'])}  (n={s['n']}, successes={s['successes']})")
    if summary.vulnerable_top3:
        lines.append(f"  vulnerable top3: {', '.join(summary.vulnerable_top3)}")
    return lines


def _category_section(summary: Summary) -> list[str]:
    """카테고리 등장 횟수 섹션."""
    lines = ["", "Per-category (detection counts):"]
    for cat, cnt in sorted(summary.per_category.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"  {cat:<16} {cnt}")
    return lines


def render_table(summary: Summary) -> str:
    """Summary 를 사람이 읽는 ASCII 요약표 문자열로 렌더한다."""
    o = summary.overall
    total = o.get("total", 0)
    successes = o.get("successes", 0)
    asr = o.get("asr", 0.0)

    lines: list[str] = [
        "=" * 60,
        "redteam run summary",
        "=" * 60,
        f"overall: {successes}/{total} success  (ASR {_pct(asr)})   "
        f"judge_agreement {_pct(summary.judge_agreement)}",
        "",
    ]
    lines += _technique_table(summary)
    lines += _domain_section(summary)
    lines += _category_section(summary)
    return "\n".join(lines) + "\n"
