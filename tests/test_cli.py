"""`rt` CLI 진입점 스모크 테스트."""

import yaml
from typer.testing import CliRunner

from redteam import __version__
from redteam import runner as runner_mod
from redteam.cli import app

runner = CliRunner()


def test_version_flag_prints_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_help_shows_usage() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


_CFG = """
target: {base_url: "-", model: "-", adapter: "manual"}
detectors: [refusal_match]
techniques: [flip_attack, past_tense]
behaviors: {source: builtin, limit: 2}
budget: {target_calls: 5}
reporting: {html: false}
"""


def _write_cfg(tmp_path, text=_CFG) -> str:
    p = tmp_path / "run.yaml"
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_run_command_listed_in_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


def test_run_dry_run_prints_plan_without_executing(tmp_path) -> None:
    result = runner.invoke(app, ["run", "-c", _write_cfg(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    assert "flip_attack" in result.stdout
    assert "dry-run" in result.stdout.lower()


def test_run_dry_run_applies_override(tmp_path) -> None:
    result = runner.invoke(
        app,
        ["run", "-c", _write_cfg(tmp_path), "--set", "budget.target_calls=99", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "99" in result.stdout


def test_run_config_error_exits_nonzero(tmp_path) -> None:
    bad = _CFG + '\njudge: {base_url: "-", model: "-"}\n'  # judge == target(자기 채점)
    result = runner.invoke(app, ["run", "-c", _write_cfg(tmp_path, bad), "--dry-run"])
    assert result.exit_code != 0


def test_run_executes_runner_and_prints_result(tmp_path, monkeypatch, fake_adapter) -> None:
    """non-dry 경로: CLI→runner.run 에 snapshot=raw·out_root=--out 전달, 요약표·산출물 경로 출력."""
    real_run = runner_mod.run
    target = fake_adapter(responses="물론이죠, 다음과 같습니다 ...")  # manual input() 미경유
    seen: dict = {}

    def spy(cfg, **kwargs):
        seen.update(kwargs)
        seen["result"] = real_run(cfg, target=target, timestamp="TS", **kwargs)
        return seen["result"]

    monkeypatch.setattr(runner_mod, "run", spy)
    out = tmp_path / "out"
    result = runner.invoke(app, ["run", "-c", _write_cfg(tmp_path), "--out", str(out)])

    assert result.exit_code == 0, result.output
    assert seen["out_root"] == str(out)
    assert seen["snapshot"] == yaml.safe_load(_CFG)  # load_config 의 raw 그대로
    assert len(target.calls) == 4  # 2 기법 × 2 behavior 실제 실행
    res = seen["result"]
    assert res.out_dir == out / "TS"
    assert all(p.exists() for p in res.paths.values())  # attempts/summary/config
    assert res.table in result.stdout
    assert f"산출물: {res.out_dir}" in result.stdout
