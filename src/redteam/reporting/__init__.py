"""reporting — 결과·지표 집계와 산출물 렌더.

공개 API: summarize/Summary(순수 집계), write_run(JSONL·JSON·YAML 산출), render_table(ASCII 표),
render_html/write_html(자기완결 HTML 리포트).
"""

from redteam.reporting.aggregate import Summary, summarize
from redteam.reporting.html_report import render_html, write_html
from redteam.reporting.jsonl_writer import write_run
from redteam.reporting.terminal_table import render_table

__all__ = [
    "Summary",
    "summarize",
    "write_run",
    "render_table",
    "render_html",
    "write_html",
]
