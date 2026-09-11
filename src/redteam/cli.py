"""redteam CLI 진입점 (`rt`)."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml

from redteam import __version__, runner
from redteam.behaviors import load_behaviors
from redteam.config_loader import load_config
from redteam.core import ConfigError, RunConfig

app = typer.Typer(
    name="rt",
    help="범용 블랙박스 LLM red-teaming 도구.",
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="버전을 출력하고 종료합니다.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """redteam 루트 명령. 서브커맨드는 프로젝트 단계에서 추가된다."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


def _parse_overrides(items: list[str] | None) -> dict[str, object]:
    """`key=value` 목록을 dotted-key 오버라이드 dict 로 변환 (value 는 YAML 스칼라로 해석)."""
    out: dict[str, object] = {}
    for item in items or []:
        if "=" not in item:
            raise typer.BadParameter(f"--set 는 key=value 형식이어야 합니다: {item!r}")
        key, raw = item.split("=", 1)
        out[key.strip()] = yaml.safe_load(raw)
    return out


def _plan_text(cfg: RunConfig, n_behaviors: int) -> str:
    """실행 계획 요약(dry-run·헤더용)."""
    detectors = ", ".join(d.name for d in cfg.detectors)
    techniques = ", ".join(cfg.techniques)
    return (
        "실행 계획:\n"
        f"  techniques : {techniques}\n"
        f"  detectors  : {detectors} (primary={cfg.detectors[0].name})\n"
        f"  behaviors  : {cfg.behaviors.source} × {n_behaviors}건\n"
        f"  budget(B)  : {cfg.budget}\n"
        f"  out_dir    : {cfg.out_dir}"
    )


@app.command()
def run(
    config: Path = typer.Option(..., "-c", "--config", help="run-config YAML 경로"),
    set_: list[str] | None = typer.Option(
        None, "--set", "-s", help="오버라이드 key=value (dotted, YAML 값). 반복 가능"
    ),
    out: str | None = typer.Option(None, "--out", help="출력 루트 디렉터리 오버라이드"),
    dry_run: bool = typer.Option(False, "--dry-run", help="실행 없이 계획만 출력"),
    allow_self_judge: bool = typer.Option(
        False, "--allow-self-judge", help="target==judge(자기 채점) 허용"
    ),
) -> None:
    """run-config 로 red-teaming 을 실행한다 (기법×behavior → 판정 → 산출물)."""
    overrides = _parse_overrides(set_)
    try:
        cfg, raw = load_config(config, overrides, allow_self_judge=allow_self_judge)
        behaviors = load_behaviors(cfg.behaviors)
    except ConfigError as e:
        typer.echo(f"[config 오류] {e}", err=True)
        raise typer.Exit(1) from e

    typer.echo(_plan_text(cfg, len(behaviors)))
    if dry_run:
        typer.echo("[dry-run] 실행하지 않고 종료합니다.")
        return

    result = runner.run(cfg, snapshot=raw, out_root=out)
    typer.echo(result.table)
    typer.echo(f"산출물: {result.out_dir}")


if __name__ == "__main__":
    app()
