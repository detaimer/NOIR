"""core.interfaces — Adapter Protocol(구조적)·Detector/Probe ABC·ProbeContext."""

from __future__ import annotations

import random

import pytest

itf = pytest.importorskip("redteam.core.interfaces")
rec = pytest.importorskip("redteam.core.records")


class _DuckAdapter:
    """Adapter Protocol 을 상속 없이 구조적으로 만족하는 fake."""

    name = "duck"

    def chat(self, messages):
        return "chat-reply"

    def generate(self, prompt, system=None):
        return "gen-reply"


def test_adapter_is_runtime_checkable_protocol():
    d = _DuckAdapter()
    # 상속 없이도 구조적으로 Adapter
    assert isinstance(d, itf.Adapter)
    assert d.chat([]) == "chat-reply"
    assert d.generate("p") == "gen-reply"


def test_non_adapter_fails_isinstance():
    class NotAdapter:
        pass

    assert not isinstance(NotAdapter(), itf.Adapter)


def test_detector_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        itf.Detector()  # 추상 judge() 미구현


def test_detector_subclass_works():
    class MyJudge(itf.Detector):
        name = "myjudge"

        def judge(self, behavior, prompt, response, conversation=None):
            return rec.DetectionResult(success=True, judge_name=self.name)

    j = MyJudge()
    assert isinstance(j, itf.Detector)
    out = j.judge(None, "p", "r")
    assert out.success is True
    assert out.judge_name == "myjudge"


def test_probe_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        itf.Probe()  # 추상 run() 미구현


def test_probe_subclass_works():
    class MyProbe(itf.Probe):
        name = "myprobe"
        uses_attacker = False
        uses_judge = True
        default_turns = 1

        def run(self, behavior, ctx):
            return "ran"

    p = MyProbe()
    assert isinstance(p, itf.Probe)
    assert p.uses_attacker is False
    assert p.default_turns == 1
    assert p.run(None, None) == "ran"


def test_probe_context_holds_injected_collaborators():
    target = _DuckAdapter()

    class J(itf.Detector):
        name = "j"

        def judge(self, behavior, prompt, response, conversation=None):
            return rec.DetectionResult(success=False, judge_name="j")

    ctx = itf.ProbeContext(
        target=target,
        judge=J(),
        attacker=None,
        max_turns=5,
        max_attempts=10,
        rng=random.Random(0),
    )
    assert ctx.target is target
    assert ctx.attacker is None
    assert ctx.max_turns == 5
    assert ctx.max_attempts == 10
    assert isinstance(ctx.rng, random.Random)


def test_probe_context_new_fields_defaults_and_settable():
    target = _DuckAdapter()

    class J(itf.Detector):
        name = "j"

        def judge(self, behavior, prompt, response, conversation=None):
            return rec.DetectionResult(success=False, judge_name="j")

    ctx = itf.ProbeContext(
        target=target,
        judge=J(),
        attacker=None,
        max_turns=1,
        max_attempts=1,
        rng=random.Random(0),
    )
    assert ctx.judge_client is None
    assert ctx.params == {}

    jc = _DuckAdapter()
    ctx2 = itf.ProbeContext(
        target=target,
        judge=J(),
        attacker=None,
        max_turns=1,
        max_attempts=1,
        rng=random.Random(0),
        judge_client=jc,
        params={"n_streams": 3},
    )
    assert ctx2.judge_client is jc
    assert ctx2.params == {"n_streams": 3}
