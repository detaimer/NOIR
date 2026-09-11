"""jsonl_writer.write_run 검증 — 파일 생성·JSONL 왕복·config redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytest.importorskip("redteam.reporting.jsonl_writer")

from redteam.core import Attempt, Behavior, DetectionResult, Turn  # noqa: E402
from redteam.reporting.aggregate import summarize  # noqa: E402
from redteam.reporting.jsonl_writer import write_run  # noqa: E402


def _attempt(behavior_id: str, success: bool) -> Attempt:
    return Attempt(
        behavior_id=behavior_id,
        technique="flip_attack",
        turns=(Turn(prompt="p1", response="r1"),),
        final_prompt="p1",
        final_response="r1",
        detections=(
            DetectionResult(success=success, judge_name="refusal_match", categories=("x",)),
        ),
        success=success,
        target_calls=2,
    )


@pytest.fixture
def run_data():
    attempts = [_attempt("b1", True), _attempt("b2", False)]
    behaviors = [
        Behavior(id="b1", prompt="p", domain="cyber"),
        Behavior(id="b2", prompt="p", domain="ot_ics"),
    ]
    summary = summarize(attempts, behaviors)
    config = {
        "target": {"api_key": "sk-SECRET123", "api_key_env": "T_KEY", "model": "gpt-x"},
        "budget": {"target_calls": 50},
    }
    return attempts, summary, config


def test_writes_three_files(tmp_path, run_data):
    attempts, summary, config = run_data
    paths = write_run(tmp_path, attempts, summary, config)
    assert (tmp_path / "attempts.jsonl").exists()
    assert (tmp_path / "summary.json").exists()
    assert (tmp_path / "config.snapshot.yaml").exists()
    assert set(paths) == {"attempts", "summary", "config"}
    assert all(isinstance(p, Path) for p in paths.values())


def test_creates_missing_out_dir(tmp_path, run_data):
    attempts, summary, config = run_data
    nested = tmp_path / "runs" / "20260101"
    write_run(nested, attempts, summary, config)
    assert (nested / "attempts.jsonl").exists()


def test_attempts_jsonl_roundtrip(tmp_path, run_data):
    attempts, summary, config = run_data
    write_run(tmp_path, attempts, summary, config)
    lines = (tmp_path / "attempts.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    recs = [json.loads(ln) for ln in lines]
    assert recs[0]["behavior_id"] == "b1"
    assert recs[0]["success"] is True
    # tuples serialize as JSON arrays
    assert isinstance(recs[0]["turns"], list)
    assert isinstance(recs[0]["detections"], list)
    assert recs[0]["detections"][0]["judge_name"] == "refusal_match"
    assert recs[0]["detections"][0]["categories"] == ["x"]


def test_summary_json_roundtrip(tmp_path, run_data):
    attempts, summary, config = run_data
    write_run(tmp_path, attempts, summary, config)
    data = json.loads((tmp_path / "summary.json").read_text())
    assert data["overall"]["total"] == 2
    assert "flip_attack" in data["per_technique"]


def test_config_snapshot_redacts_secret_keeps_env_name(tmp_path, run_data):
    attempts, summary, config = run_data
    write_run(tmp_path, attempts, summary, config)
    text = (tmp_path / "config.snapshot.yaml").read_text()
    assert "sk-SECRET123" not in text  # secret value gone
    assert "***" in text
    assert "T_KEY" in text  # api_key_env holds an env-var NAME, not a secret
    # snapshot still parses and env name is preserved under api_key_env
    loaded = yaml.safe_load(text)
    assert loaded["target"]["api_key"] == "***"
    assert loaded["target"]["api_key_env"] == "T_KEY"
    assert loaded["target"]["model"] == "gpt-x"


def test_redaction_case_insensitive_and_nested(tmp_path, run_data):
    attempts, summary, _ = run_data
    config = {
        "a": {"API_KEY": "sk-1", "Token": "tok-2", "nested": {"Password": "pw", "Secret": "s"}},
        "list": [{"apikey": "sk-3"}],
        "keep": "visible",
    }
    write_run(tmp_path, attempts, summary, config)
    text = (tmp_path / "config.snapshot.yaml").read_text()
    for leaked in ("sk-1", "tok-2", "pw", "sk-3"):
        assert leaked not in text
    assert "visible" in text
    loaded = yaml.safe_load(text)
    assert loaded["a"]["nested"]["Secret"] == "***"
    assert loaded["list"][0]["apikey"] == "***"


def test_does_not_mutate_input_config(tmp_path, run_data):
    attempts, summary, config = run_data
    write_run(tmp_path, attempts, summary, config)
    assert config["target"]["api_key"] == "sk-SECRET123"  # original untouched
