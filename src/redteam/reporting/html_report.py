"""HTML 리포트 렌더 — summarize() 결과 + attempts 를 자기완결 단일 HTML 로.

정보설계 중심(도메인×기법 위험도 히트맵 강조, docs/evaluation.md). 지표 계산은 하지 않고
`aggregate.Summary` 를 그대로 표시한다(단일 집계 소스). 외부 CDN/폰트를 참조하지 않으므로
오프라인에서 파일 하나만 열면 된다. 타깃 응답은 신뢰할 수 없는 텍스트이므로 autoescape 필수.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment

from redteam.core import Attempt, Behavior
from redteam.reporting.aggregate import Summary

SECTIONS: tuple[str, ...] = (
    "개요",
    "기법 비교 (Fair-ASR)",
    "위험도 히트맵 (도메인 × 기법)",
    "취약 도메인 Top 3",
    "카테고리 분포",
    "Taxonomy 커버리지",
    "Judge 합치도",
    "시도 드릴다운",
)

# 히트맵 셀 위험도 등급 (ASR 구간 → 등급). 0% 와 '미측정'(셀 없음)은 구분한다.
_RISK_BANDS = ((0.0, "none"), (0.34, "low"), (0.67, "mid"), (1.01, "high"))

_REPORT_FILENAME = "report.html"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def _num(x: float) -> str:
    return f"{x:.2f}"


def _score(x: float | None) -> str:
    """등급 judge 는 0~1 점수, 이진 judge 는 score=None → 'N/A'."""
    return "N/A" if x is None else f"{x:.2f}"


def _risk(asr: float) -> str:
    """ASR → 위험도 등급 문자열 (셀 색농도용)."""
    for upper, name in _RISK_BANDS:
        if asr <= upper:
            return name
    return "high"


def _behavior_map(
    behaviors: list[Behavior] | dict[str, Behavior] | None,
) -> dict[str, Behavior]:
    """behaviors 를 id→Behavior 맵으로 정규화 (list/dict/None 수용)."""
    if behaviors is None:
        return {}
    if isinstance(behaviors, dict):
        return dict(behaviors)
    return {b.id: b for b in behaviors}


def _technique_rows(summary: Summary) -> list[dict]:
    """기법 비교표 행 — ASR 내림차순, 동점은 이름순(터미널 표와 동일 정렬)."""
    return [
        {
            "technique": tech,
            "n": s["n"],
            "asr": _pct(s["asr"]),
            "avg_calls": _num(s["avg_target_calls"]),
            "efficiency": _num(s["efficiency"]),
            "sr_avg": _num(s["strong_reject_avg"]),
        }
        for tech, s in sorted(summary.per_technique.items(), key=lambda kv: (-kv[1]["asr"], kv[0]))
    ]


def _heatmap_view(summary: Summary) -> dict:
    """히트맵 행렬 — 열은 전 기법 합집합, 시도 없는 칸은 None(미측정)."""
    techniques = sorted({t for row in summary.heatmap.values() for t in row})
    rows = []
    for domain, row in sorted(
        summary.heatmap.items(), key=lambda kv: (-max(c["asr"] for c in kv[1].values()), kv[0])
    ):
        cells = []
        for tech in techniques:
            cell = row.get(tech)
            cells.append(
                None
                if cell is None
                else {
                    "asr": _num(cell["asr"]),
                    "label": _pct(cell["asr"]),
                    "risk": _risk(cell["asr"]),
                    "n": cell["n"],
                    "successes": cell["successes"],
                }
            )
        rows.append({"domain": domain, "cells": cells})
    return {"techniques": techniques, "rows": rows}


def _judge_rows(attempts: list[Attempt]) -> list[dict]:
    """judge 별 성공 판정 대비표 — 합치도 수치를 뒷받침하는 분해."""
    stats: dict[str, dict] = {}
    for a in attempts:
        for d in a.detections:
            s = stats.setdefault(d.judge_name, {"n": 0, "successes": 0, "scores": []})
            s["n"] += 1
            s["successes"] += int(d.success)
            if d.score is not None:
                s["scores"].append(d.score)
    rows = []
    for name, s in sorted(stats.items()):
        rows.append(
            {
                "judge": name,
                "n": s["n"],
                "successes": s["successes"],
                "asr": _pct(s["successes"] / s["n"]) if s["n"] else _pct(0.0),
                "score_avg": _score(sum(s["scores"]) / len(s["scores"]) if s["scores"] else None),
            }
        )
    return rows


def _drilldown(attempts: list[Attempt], bmap: dict[str, Behavior]) -> list[dict]:
    """시도별 상세 — 성공 건을 먼저 보여 준다(조사 동선)."""
    items = []
    for a in attempts:
        b = bmap.get(a.behavior_id)
        items.append(
            {
                "behavior_id": a.behavior_id,
                "technique": a.technique,
                "success": a.success,
                "target_calls": a.target_calls,
                "attacker_calls": a.attacker_calls,
                "judge_calls": a.judge_calls,
                "budget_exhausted": a.budget_exhausted,
                "error": a.error,
                "domain": b.domain if b is not None else "unknown",
                "subcat": b.subcat if b is not None else "",
                "tags": list(b.tags) if b is not None else [],
                "prompt": b.prompt if b is not None else "",
                "turns": [{"prompt": t.prompt, "response": t.response} for t in a.turns],
                "detections": [
                    {
                        "judge": d.judge_name,
                        "success": d.success,
                        "score": _score(d.score),
                        "categories": list(d.categories),
                        "rationale": d.rationale or "",
                    }
                    for d in a.detections
                ],
            }
        )
    return sorted(items, key=lambda it: (not it["success"], it["behavior_id"], it["technique"]))


def _sorted_counts(counts: dict[str, int]) -> list[tuple[str, int]]:
    """빈도 내림차순, 동점은 이름순."""
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))


def _sorted_stats(stats: dict[str, dict]) -> list[tuple[str, dict]]:
    """ASR 내림차순, 동점은 n 내림차순 → 이름순."""
    return sorted(stats.items(), key=lambda kv: (-kv[1]["asr"], -kv[1]["n"], kv[0]))


_CSS = """
:root { color-scheme: light; }
body { margin: 0; padding: 24px; color: #16181d; background: #f6f7f9;
       font: 14px/1.55 system-ui, -apple-system, "Noto Sans KR", sans-serif; }
main { max-width: 1100px; margin: 0 auto; }
h1 { font-size: 22px; margin: 0 0 4px; }
h2 { font-size: 16px; margin: 0 0 12px; padding-bottom: 6px; border-bottom: 2px solid #e3e6ea; }
section { background: #fff; border: 1px solid #e3e6ea; border-radius: 8px;
          padding: 18px 20px; margin-bottom: 16px; }
.sub { color: #667085; font-size: 12px; margin: 0 0 20px; }
.kpis { display: flex; flex-wrap: wrap; gap: 12px; }
.kpi { flex: 1 1 140px; border: 1px solid #e3e6ea; border-radius: 6px; padding: 10px 12px; }
.kpi .v { font-size: 22px; font-weight: 600; }
.kpi .k { color: #667085; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; }
th, td { padding: 7px 10px; border-bottom: 1px solid #eceef1; text-align: right; }
th:first-child, td:first-child { text-align: left; }
thead th { background: #f2f4f7; font-size: 12px; color: #475467; }
.heat td.cell { text-align: center; font-weight: 600; border: 1px solid #fff; }
.heat td[data-risk="none"] { background: #e8f5e9; }
.heat td[data-risk="low"]  { background: #fff4cc; }
.heat td[data-risk="mid"]  { background: #ffd8a8; }
.heat td[data-risk="high"] { background: #ffb3b3; }
.heat td.cell-empty { color: #98a2b3; text-align: center;
  background: repeating-linear-gradient(45deg,#fafafa,#fafafa 6px,#f0f0f0 6px,#f0f0f0 12px); }
.pill { display: inline-block; padding: 1px 7px; border-radius: 10px; font-size: 11px;
        background: #eef0f3; color: #475467; margin-right: 4px; }
.ok { color: #b42318; font-weight: 600; }   /* 공격 성공 = 방어 실패 */
.no { color: #067647; }
details { border: 1px solid #e3e6ea; border-radius: 6px; margin-bottom: 8px; }
details > summary { cursor: pointer; padding: 9px 12px; background: #fafbfc; }
details .body { padding: 10px 14px; }
pre { white-space: pre-wrap; word-break: break-word; background: #f7f8fa; border: 1px solid #eceef1;
      border-radius: 4px; padding: 8px 10px; margin: 4px 0 10px; font-size: 12.5px; }
.empty { color: #98a2b3; font-style: italic; }
"""

_TEMPLATE = """<!doctype html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>redteam 리포트</title>
<style>{{ css }}</style></head>
<body><main>
<h1>redteam 리포트</h1>
<p class="sub">target: {{ meta.target }} &middot; budget B: {{ meta.budget }}
  &middot; run: {{ meta.timestamp }}</p>

<section>
  <h2>{{ sections[0] }}</h2>
  <div class="kpis">
    <div class="kpi"><div class="k">overall ASR</div><div class="v">{{ overall.asr }}</div></div>
    <div class="kpi"><div class="k">successes</div>
      <div class="v">{{ overall.successes }}</div></div>
    <div class="kpi"><div class="k">attempts</div><div class="v">{{ overall.total }}</div></div>
    <div class="kpi"><div class="k">judge 합치도</div><div class="v">{{ agreement }}</div></div>
  </div>
  <p class="sub" style="margin-top:14px">ASR 은 헤드라인 지표일 뿐이다 —
    아래 efficiency·도메인/taxonomy 분해·judge 합치도를 함께 본다.</p>
</section>

<section>
  <h2>{{ sections[1] }}</h2>
  {% if technique_rows %}
  <table><thead><tr>
    <th>technique</th><th>n</th><th>ASR@B</th><th>avg_calls</th><th>efficiency</th><th>SR_avg</th>
  </tr></thead><tbody>
  {% for r in technique_rows %}
    <tr><td>{{ r.technique }}</td><td>{{ r.n }}</td><td>{{ r.asr }}</td>
        <td>{{ r.avg_calls }}</td><td>{{ r.efficiency }}</td><td>{{ r.sr_avg }}</td></tr>
  {% endfor %}
  </tbody></table>
  {% else %}<p class="empty">시도 없음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[2] }}</h2>
  {% if heatmap.rows %}
  <table class="heat"><thead><tr><th>domain \\ technique</th>
    {% for t in heatmap.techniques %}<th style="text-align:center">{{ t }}</th>{% endfor %}
  </tr></thead><tbody>
  {% for row in heatmap.rows %}
    <tr><td>{{ row.domain }}</td>
    {% for c in row.cells %}
      {% if c %}<td class="cell" data-asr="{{ c.asr }}" data-risk="{{ c.risk }}"
             title="{{ c.successes }}/{{ c.n }} 성공">{{ c.label }}</td>
      {% else %}<td class="cell cell-empty" title="시도 없음">&middot;</td>{% endif %}
    {% endfor %}
    </tr>
  {% endfor %}
  </tbody></table>
  {% else %}<p class="empty">시도 없음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[3] }}</h2>
  {% if top3 %}<ol>{% for d in top3 %}
    <li><strong>{{ d }}</strong> — ASR {{ per_domain[d].asr }}
      ({{ per_domain[d].successes }}/{{ per_domain[d].n }})</li>
  {% endfor %}</ol>{% else %}<p class="empty">시도 없음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[4] }}</h2>
  {% if categories %}
  <table><thead><tr><th>category</th><th>count</th></tr></thead><tbody>
  {% for name, cnt in categories %}<tr><td>{{ name }}</td><td>{{ cnt }}</td></tr>{% endfor %}
  </tbody></table>
  {% else %}<p class="empty">judge 가 카테고리를 반환하지 않음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[5] }}</h2>
  {% if tags %}
  <table><thead><tr><th>tag</th><th>n</th><th>successes</th><th>ASR</th></tr></thead><tbody>
  {% for name, s in tags %}
    <tr><td>{{ name }}</td><td>{{ s.n }}</td><td>{{ s.successes }}</td><td>{{ s.asr }}</td></tr>
  {% endfor %}</tbody></table>
  {% else %}<p class="empty">behavior 에 taxonomy 태그 없음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[6] }}</h2>
  <p>모든 judge 가 동일 판정을 낸 시도 비율: <strong>{{ agreement }}</strong></p>
  {% if judge_rows %}
  <table><thead><tr><th>judge</th><th>판정 수</th><th>success</th>
    <th>success 율</th><th>평균 score</th></tr></thead><tbody>
  {% for r in judge_rows %}
    <tr><td>{{ r.judge }}</td><td>{{ r.n }}</td><td>{{ r.successes }}</td>
        <td>{{ r.asr }}</td><td>{{ r.score_avg }}</td></tr>
  {% endfor %}</tbody></table>
  {% else %}<p class="empty">판정 없음</p>{% endif %}
</section>

<section>
  <h2>{{ sections[7] }}</h2>
  {% if drilldown %}
  {% for it in drilldown %}
  <details>
    <summary>
      <span class="{{ 'ok' if it.success else 'no' }}">{{ '성공' if it.success else '실패' }}</span>
      &middot; {{ it.behavior_id }} &middot; {{ it.technique }} &middot; {{ it.domain }}
      {% if it.subcat %}/{{ it.subcat }}{% endif %}
      &middot; target_calls {{ it.target_calls }}
      {% if it.budget_exhausted %}&middot; <span class="pill">budget 소진</span>{% endif %}
      {% if it.error %}&middot; <span class="pill">error</span>{% endif %}
    </summary>
    <div class="body">
      {% if it.prompt %}<p><strong>behavior</strong>: {{ it.prompt }}</p>{% endif %}
      {% if it.tags %}<p>
        {% for t in it.tags %}<span class="pill">{{ t }}</span>{% endfor %}</p>{% endif %}
      {% if it.error %}<p><strong>error</strong>: {{ it.error }}</p>{% endif %}
      <p><strong>transcript</strong> ({{ it.turns|length }} turn,
        attacker_calls {{ it.attacker_calls }}, judge_calls {{ it.judge_calls }})</p>
      {% for t in it.turns %}
        <div><span class="pill">turn {{ loop.index }} · prompt</span><pre>{{ t.prompt }}</pre></div>
        <div><span class="pill">turn {{ loop.index }} · response</span>
          <pre>{{ t.response }}</pre></div>
      {% endfor %}
      <p><strong>judges</strong></p>
      <table><thead><tr><th>judge</th><th>success</th><th>score</th><th>categories</th><th>rationale</th></tr></thead><tbody>
      {% for d in it.detections %}
        <tr><td>{{ d.judge }}</td>
            <td class="{{ 'ok' if d.success else 'no' }}">{{ d.success }}</td>
            <td>{{ d.score }}</td>
            <td>{{ d.categories|join(', ') }}</td>
            <td style="text-align:left">{{ d.rationale }}</td></tr>
      {% endfor %}</tbody></table>
    </div>
  </details>
  {% endfor %}
  {% else %}<p class="empty">시도 없음</p>{% endif %}
</section>
</main></body></html>
"""


def render_html(
    summary: Summary,
    attempts: list[Attempt],
    behaviors: list[Behavior] | dict[str, Behavior] | None = None,
    meta: dict | None = None,
) -> str:
    """Summary+attempts → 자기완결 HTML 문서 문자열 (I/O 없음)."""
    meta = {"target": "-", "budget": "-", "timestamp": "-", **(meta or {})}
    bmap = _behavior_map(behaviors)
    env = Environment(autoescape=True, trim_blocks=True, lstrip_blocks=True)
    return env.from_string(_TEMPLATE).render(
        css=_CSS,
        sections=SECTIONS,
        meta=meta,
        overall={
            "asr": _pct(summary.overall.get("asr", 0.0)),
            "successes": summary.overall.get("successes", 0),
            "total": summary.overall.get("total", 0),
        },
        agreement=_pct(summary.judge_agreement),
        technique_rows=_technique_rows(summary),
        heatmap=_heatmap_view(summary),
        top3=summary.vulnerable_top3,
        per_domain={
            d: {"asr": _pct(s["asr"]), "successes": s["successes"], "n": s["n"]}
            for d, s in summary.per_domain.items()
        },
        categories=_sorted_counts(summary.per_category),
        tags=[
            (name, {"n": s["n"], "successes": s["successes"], "asr": _pct(s["asr"])})
            for name, s in _sorted_stats(summary.per_tag)
        ],
        judge_rows=_judge_rows(attempts),
        drilldown=_drilldown(attempts, bmap),
    )


def write_html(
    out_dir: str | Path,
    summary: Summary,
    attempts: list[Attempt],
    behaviors: list[Behavior] | dict[str, Behavior] | None = None,
    meta: dict | None = None,
) -> Path:
    """out_dir 에 report.html 을 쓰고 경로를 반환한다 (부모 디렉터리 자동 생성)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / _REPORT_FILENAME
    path.write_text(render_html(summary, attempts, behaviors, meta), encoding="utf-8")
    return path
