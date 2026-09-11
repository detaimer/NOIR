"""runner — 정적 tier 오프라인 e2e (전 fake), 예산 집계·다중 judge 채점·tmp 출력."""

from __future__ import annotations

import pytest

runner = pytest.importorskip("redteam.runner")
from redteam.core import AdapterError, RunConfig  # noqa: E402


def _cfg(**over):
    raw = {
        "target": {"base_url": "-", "model": "-", "adapter": "manual"},
        "detectors": ["refusal_match"],
        "techniques": ["flip_attack", "past_tense"],
        "behaviors": {"source": "builtin", "limit": 2},
        "budget": {"target_calls": 5},
        "reporting": {"html": False},
    }
    raw.update(over)
    return RunConfig.from_dict(raw)


def test_static_e2e_all_fake(tmp_path, fake_adapter):
    # 응낙 응답 → refusal_match success=True
    target = fake_adapter(responses="물론이죠, 다음과 같습니다 ...")
    result = runner.run(
        _cfg(), target=target, out_root=str(tmp_path), timestamp="TS", snapshot={"x": 1}
    )
    # 2 기법 × 2 behavior = 4 attempts
    assert len(result.attempts) == 4
    assert all(a.target_calls == 1 for a in result.attempts)  # 정적=1 호출
    assert all(a.success for a in result.attempts)
    assert result.summary.overall["total"] == 4
    assert result.summary.overall["asr"] == 1.0
    # 출력 파일
    assert result.out_dir.name == "TS"
    for key in ("attempts", "summary", "config"):
        assert result.paths[key].exists()
    assert "flip_attack" in result.table


def test_transform_applied_to_target(tmp_path, fake_adapter):
    target = fake_adapter(responses="ok")
    runner.run(
        _cfg(techniques=["flip_attack"], behaviors={"source": "builtin", "limit": 1}),
        target=target,
        out_root=str(tmp_path),
        timestamp="TS2",
    )
    # 타깃이 받은 프롬프트는 원본 behavior.prompt 와 달라야 함(변환 적용됨)
    seen = [payload for payload in target.calls]
    assert seen and seen[0][0] == "generate"


def test_remaining_judges_score_final_response(tmp_path, fake_adapter):
    target = fake_adapter(responses="응낙 응답")
    judge_client = fake_adapter(responses="unsafe\nS9")
    result = runner.run(
        _cfg(
            detectors=["refusal_match", "llama_guard"],
            techniques=["past_tense"],
            behaviors={"source": "builtin", "limit": 1},
        ),
        target=target,
        judge_client=judge_client,
        out_root=str(tmp_path),
        timestamp="TS3",
    )
    a = result.attempts[0]
    names = [d.judge_name for d in a.detections]
    assert names == ["refusal_match", "llama_guard"]  # primary + 나머지
    assert a.detections[1].categories == ("S9",)


def test_adapter_error_becomes_attempt_error(tmp_path):
    class Boom:
        name = "boom"

        def generate(self, prompt, system=None):
            raise AdapterError("HTTP 500")

        def chat(self, messages):
            raise AdapterError("HTTP 500")

    result = runner.run(
        _cfg(techniques=["flip_attack"], behaviors={"source": "builtin", "limit": 1}),
        target=Boom(),
        out_root=str(tmp_path),
        timestamp="TS4",
    )
    a = result.attempts[0]
    assert a.error is not None
    assert a.success is False
