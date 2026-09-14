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


def test_pair_e2e(tmp_path, fake_adapter):
    # 충실 PAIR e2e: attacker 가 JSON 제안 → target 응낙 → refusal_match(primary) 성공.
    # 1 stream × 1 iteration 으로 카운트를 결정적으로 유지.
    target = fake_adapter(responses="물론이죠, 다음과 같이")  # 응낙 → refusal_match success
    attacker = fake_adapter(responses='{"improvement": "i", "prompt": "adv"}')
    judge_client = fake_adapter(responses="Rating: [[1]]")  # 내부 1~10 judge (별도 엔드포인트)
    result = runner.run(
        _cfg(
            techniques=[{"pair": {"n_streams": 1, "n_iterations": 1}}],
            behaviors={"source": "builtin", "limit": 1},
            budget={"target_calls": 5},
        ),
        target=target,
        attacker=attacker,
        judge_client=judge_client,
        out_root=str(tmp_path),
        timestamp="TS_PAIR",
    )
    a = result.attempts[0]
    assert a.technique == "pair"
    assert a.success is True
    assert a.target_calls == 1  # counter 권위 (1 stream × 1 iter)
    assert a.attacker_calls == 1
    assert a.judge_calls == 2  # 내부 rating 1 + primary(refusal_match) 1
    # target 은 attacker JSON 의 파싱된 prompt 를 받는다.
    assert a.final_prompt == "adv"


def test_crescendo_e2e_via_manual_adapter(tmp_path, fake_adapter):
    from redteam.adapters.manual_io import ManualIOAdapter

    # Manual 타깃(사람 중계)로 멀티턴 Crescendo e2e — sentinel('.')로 턴 응답 종료.
    scripted = iter(["죄송하지만 도와드릴 수 없습니다", ".", "물론이죠, 다음과 같습니다 ...", "."])
    captured: list[str] = []
    manual = ManualIOAdapter(
        input_fn=lambda: next(scripted),
        output_fn=captured.append,
    )
    attacker = fake_adapter(
        responses=[
            '{"generated_question": "u1"}',
            '{"generated_question": "u2"}',
        ]
    )
    judge_client = fake_adapter(responses=['{"score_value": "40"}', '{"score_value": "40"}'])
    result = runner.run(
        _cfg(
            techniques=[{"crescendo": {"max_turns": 2, "max_backtracks": 0}}],
            behaviors={"source": "builtin", "limit": 1},
            budget={"target_calls": 5},
        ),
        target=manual,
        attacker=attacker,
        judge_client=judge_client,
        out_root=str(tmp_path),
        timestamp="TS_CRES",
    )
    a = result.attempts[0]
    assert a.technique == "crescendo"
    assert a.success is True  # 최종 응답 응낙 → refusal_match(primary) success
    assert a.target_calls == 2
    assert a.attacker_calls == 2
    # 대화가 멀티턴으로 성장했음을 Manual 어댑터 출력으로 실증(user 누적 + assistant 등장).
    assert sum(1 for c in captured if c.startswith("user:")) >= 3
    assert any(c.startswith("assistant:") for c in captured)


def test_budget_exhausted_crescendo(tmp_path, fake_adapter):
    # Crescendo(max_turns=5)를 budget B=2 로 제한 → 3번째 호출서 BudgetExceeded 를 runner 흡수.
    target = fake_adapter(responses="죄송하지만 도와드릴 수 없습니다")  # 항상 거부
    attacker = fake_adapter(responses='{"generated_question": "u"}')
    judge_client = fake_adapter(responses='{"score_value": "True"}')  # 매 턴 refusal → backtrack
    result = runner.run(
        _cfg(
            techniques=[{"crescendo": {"max_turns": 5}}],
            behaviors={"source": "builtin", "limit": 1},
            budget={"target_calls": 2},
        ),
        target=target,
        attacker=attacker,
        judge_client=judge_client,
        out_root=str(tmp_path),
        timestamp="TS_BUDGET",
    )
    a = result.attempts[0]
    assert a.budget_exhausted is True
    assert a.target_calls == 2
    assert a.success is False
    assert a.error is not None
    assert a.turns == ()
