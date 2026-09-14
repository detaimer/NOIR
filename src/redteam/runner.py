"""오케스트레이션 — config 로 컴포넌트를 빌드하고 technique×behavior 를 실행해 산출물을 낸다.

DI/Fair-ASR: behavior 마다 새 `BudgetedTarget(limit=B)` 로 타깃을 감싸 probe 에 주입한다.
probe.run 의 예산초과/어댑터오류는 Attempt.error 로 흡수하고, primary 외 나머지 judge 는 최종
응답에 추가 채점한다. target_calls 는 counter 값을 권위로 기록한다. MVP 는 순차 실행.
테스트를 위해 target/attacker/judge_client 는 주입 가능(미주입 시 config 엔드포인트로 빌드).
"""

from __future__ import annotations

import dataclasses
import random
from datetime import datetime
from pathlib import Path

from redteam.behaviors import load_behaviors
from redteam.config_loader import resolve_api_key
from redteam.core import (
    Adapter,
    AdapterError,
    Attempt,
    BudgetedTarget,
    BudgetExceeded,
    CallCounter,
    ConfigError,
    EndpointConfig,
    ProbeContext,
    RunConfig,
)
from redteam.registry import get_adapter, get_detector, get_probe
from redteam.reporting import Summary, render_table, summarize, write_run

_UNLIMITED = 10**9


@dataclasses.dataclass
class RunResult:
    """실행 결과 묶음 (CLI·테스트가 소비)."""

    attempts: list[Attempt]
    summary: Summary
    out_dir: Path
    paths: dict[str, Path]
    table: str


def _build_adapter(ep: EndpointConfig) -> Adapter:
    """엔드포인트 설정으로 어댑터를 구성한다 (api_key 는 환경변수에서 해석)."""
    factory = get_adapter(ep.adapter)
    if ep.adapter == "manual":
        return factory(name=ep.name or "manual")
    return factory(
        model=ep.model,
        base_url=ep.base_url,
        api_key=resolve_api_key(ep),
        name=ep.name or None,
    )


def run(
    cfg: RunConfig,
    *,
    target: Adapter | None = None,
    attacker: Adapter | None = None,
    judge_client: Adapter | None = None,
    snapshot: dict | None = None,
    out_root: str | Path | None = None,
    timestamp: str | None = None,
    write: bool = True,
    seed: int = 0,
) -> RunResult:
    """config 를 실행해 Attempt 수집→집계→산출물 기록까지 수행한다."""
    if not cfg.detectors:
        raise ConfigError("최소 1개 detector(primary)가 필요합니다")

    if target is None:
        target = _build_adapter(cfg.target)
    if attacker is None and cfg.attacker is not None:
        attacker = _build_adapter(cfg.attacker)
    if judge_client is None and cfg.judge is not None:
        judge_client = _build_adapter(cfg.judge)

    detectors = [
        get_detector(spec.name, judge_client=judge_client, **spec.params) for spec in cfg.detectors
    ]
    primary = detectors[0]
    extra_detectors = detectors[1:]

    behaviors = load_behaviors(cfg.behaviors)
    budget = cfg.budget if cfg.budget and cfg.budget > 0 else _UNLIMITED
    rng = random.Random(seed)

    attempts: list[Attempt] = []
    for spec in cfg.techniques:
        probe = get_probe(spec.name)
        params = spec.params
        turns = params.get("max_turns", probe.default_turns)
        for beh in behaviors:
            counter = CallCounter()
            budgeted = BudgetedTarget(target, budget, counter)
            ctx = ProbeContext(
                target=budgeted,
                judge=primary,
                attacker=attacker,
                max_turns=turns,
                max_attempts=budget,
                rng=rng,
                judge_client=judge_client,
                params=params,
            )
            attempt = _run_one(probe, beh, spec.name, ctx, counter)
            attempt = _score_extra_judges(attempt, beh, extra_detectors)
            attempts.append(attempt)

    summary = summarize(attempts, behaviors)
    out_dir = Path(out_root or cfg.out_dir) / (
        timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    paths: dict[str, Path] = {}
    if write:
        paths = write_run(out_dir, attempts, summary, snapshot or {})
    table = render_table(summary)
    return RunResult(attempts=attempts, summary=summary, out_dir=out_dir, paths=paths, table=table)


def _run_one(probe, beh, tech, ctx, counter) -> Attempt:
    """probe.run 을 예외 안전하게 실행해 Attempt 를 만든다(오류는 Attempt.error 로)."""
    try:
        attempt = probe.run(beh, ctx)
        return dataclasses.replace(attempt, target_calls=counter.count)
    except BudgetExceeded as e:
        return _error_attempt(beh, tech, counter, budget_exhausted=True, error=str(e))
    except AdapterError as e:
        return _error_attempt(beh, tech, counter, budget_exhausted=False, error=str(e))


def _error_attempt(beh, tech, counter, *, budget_exhausted, error) -> Attempt:
    return Attempt(
        behavior_id=beh.id,
        technique=tech,
        turns=(),
        final_prompt="",
        final_response="",
        detections=(),
        success=False,
        target_calls=counter.count,
        budget_exhausted=budget_exhausted,
        error=error,
    )


def _score_extra_judges(attempt: Attempt, beh, extra_detectors) -> Attempt:
    """primary 외 나머지 judge 로 최종 응답을 추가 채점해 detections 에 덧붙인다."""
    if not attempt.final_response or not extra_detectors:
        return attempt
    extra = tuple(
        det.judge(beh, attempt.final_prompt, attempt.final_response) for det in extra_detectors
    )
    return dataclasses.replace(
        attempt,
        detections=tuple(attempt.detections) + extra,
        judge_calls=attempt.judge_calls + len(extra),
    )
