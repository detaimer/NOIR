"""redteam CLI 진입점 (`rt`)."""

from __future__ import annotations

import typer

from redteam import __version__

app = typer.Typer(
    name="rt",
    help="범용 블랙박스 LLM red-teaming 도구 (MVP 스캐폴딩).",
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


if __name__ == "__main__":
    app()
