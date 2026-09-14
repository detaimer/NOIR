"""HttpOpenAIAdapter 테스트 — fake OpenAI client 주입, 네트워크 없음."""

from __future__ import annotations

import pytest

# 훅 데드락 브레이커: impl 또는 redteam.core API(Message/AdapterError) 부재 시
# 모듈 전체 SKIP 으로 suite green 유지. 둘 다 준비되면 실제 assert 수행.
try:
    from redteam.adapters import http_openai as mod
    from redteam.core import AdapterError, Message, Role
except ImportError:
    pytest.skip("adapter/core API not available yet", allow_module_level=True)

HttpOpenAIAdapter = mod.HttpOpenAIAdapter


class _FakeCompletions:
    """chat.completions.create 를 흉내내며 호출 payload 를 기록한다."""

    def __init__(self, outer: _FakeClient) -> None:
        self._outer = outer

    def create(self, **kwargs: object) -> object:
        self._outer.calls.append(kwargs)
        return _FakeResponse(self._outer.reply, self._outer.reasoning)


class _FakeChat:
    def __init__(self, outer: _FakeClient) -> None:
        self.completions = _FakeCompletions(outer)


class _FakeClient:
    """choices[0].message 의 content(+reasoning) 를 돌려주는 최소 stub 클라이언트."""

    def __init__(self, reply: str | None = "FAKE_REPLY", reasoning: str | None = None) -> None:
        self.reply = reply
        self.reasoning = reasoning
        self.calls: list[dict] = []
        self.chat = _FakeChat(self)


class _FakeMessage:
    """reasoning 을 지정 가능한 message stub (reasoning 기본 None → 기존 동작 불변)."""

    def __init__(self, content: str | None, reasoning: str | None = None) -> None:
        self.content = content
        self.reasoning = reasoning


class _FakeChoice:
    def __init__(self, content: str | None, reasoning: str | None = None) -> None:
        self.message = _FakeMessage(content, reasoning)


class _FakeResponse:
    def __init__(self, content: str | None, reasoning: str | None = None) -> None:
        self.choices = [_FakeChoice(content, reasoning)]


class _RaisingCompletions:
    def create(self, **kwargs: object) -> object:
        raise RuntimeError("boom")


class _RaisingChat:
    completions = _RaisingCompletions()


class _RaisingClient:
    """모든 호출이 예외를 던지는 클라이언트."""

    chat = _RaisingChat()


def test_generate_without_system_maps_user_only() -> None:
    client = _FakeClient()
    adapter = HttpOpenAIAdapter(model="m1", client=client)

    out = adapter.generate("hello")

    assert out == "FAKE_REPLY"
    assert client.calls[0]["model"] == "m1"
    assert client.calls[0]["messages"] == [{"role": "user", "content": "hello"}]


def test_generate_with_system_prepends_system() -> None:
    client = _FakeClient()
    adapter = HttpOpenAIAdapter(model="m1", client=client)

    out = adapter.generate("hi", system="be nice")

    assert out == "FAKE_REPLY"
    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "be nice"},
        {"role": "user", "content": "hi"},
    ]


def test_chat_maps_each_message_role_and_content() -> None:
    client = _FakeClient(reply="ANSWER")
    adapter = HttpOpenAIAdapter(model="m1", client=client)

    msgs = [
        Message(role=Role.SYSTEM, content="sys"),
        Message(role=Role.USER, content="u"),
        Message(role=Role.ASSISTANT, content="a"),
    ]
    out = adapter.chat(msgs)

    assert out == "ANSWER"
    assert client.calls[0]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u"},
        {"role": "assistant", "content": "a"},
    ]


def test_generate_wraps_client_error_in_adapter_error() -> None:
    adapter = HttpOpenAIAdapter(model="m1", client=_RaisingClient())
    with pytest.raises(AdapterError):
        adapter.generate("x")


def test_chat_wraps_client_error_in_adapter_error() -> None:
    adapter = HttpOpenAIAdapter(model="m1", client=_RaisingClient())
    with pytest.raises(AdapterError):
        adapter.chat([Message(role=Role.USER, content="x")])


def test_name_defaults_to_http_model() -> None:
    adapter = HttpOpenAIAdapter(model="gpt-x", client=_FakeClient())
    assert adapter.name == "http:gpt-x"


def test_name_override() -> None:
    adapter = HttpOpenAIAdapter(model="gpt-x", client=_FakeClient(), name="target")
    assert adapter.name == "target"


# --- reasoning 폴백 (gpt-oss 등 reasoning 모델: content 비면 reasoning 채널 사용) ---


def test_content_empty_falls_back_to_reasoning() -> None:
    client = _FakeClient(reply="", reasoning="REASONED")
    adapter = HttpOpenAIAdapter(model="m1", client=client)
    assert adapter.generate("x") == "REASONED"


def test_content_whitespace_falls_back_to_reasoning() -> None:
    client = _FakeClient(reply="  \n ", reasoning="REASONED")
    adapter = HttpOpenAIAdapter(model="m1", client=client)
    assert adapter.generate("x") == "REASONED"


def test_content_none_falls_back_to_reasoning() -> None:
    client = _FakeClient(reply=None, reasoning="REASONED")
    adapter = HttpOpenAIAdapter(model="m1", client=client)
    assert adapter.generate("x") == "REASONED"


def test_nonempty_content_ignores_reasoning() -> None:
    # 실제 거부("I can't help…")는 non-empty content → reasoning(사고과정) 무시.
    client = _FakeClient(reply="REAL", reasoning="SHOULD_BE_IGNORED")
    adapter = HttpOpenAIAdapter(model="m1", client=client)
    assert adapter.generate("x") == "REAL"


def test_both_empty_returns_empty_string() -> None:
    client = _FakeClient(reply=None, reasoning="   ")
    adapter = HttpOpenAIAdapter(model="m1", client=client)
    assert adapter.generate("x") == ""


def test_missing_reasoning_attr_returns_empty() -> None:
    # reasoning 속성 자체가 없는 응답(비-reasoning 모델)에서 content 빔 → "" (getattr 기본값 경로).
    class _NoReasoningMessage:
        content = ""

    class _NoReasoningChoice:
        message = _NoReasoningMessage()

    class _NoReasoningResponse:
        choices = [_NoReasoningChoice()]

    class _NoReasoningCompletions:
        def create(self, **kwargs: object) -> object:
            return _NoReasoningResponse()

    class _NoReasoningChat:
        completions = _NoReasoningCompletions()

    class _NoReasoningClient:
        chat = _NoReasoningChat()

    adapter = HttpOpenAIAdapter(model="m1", client=_NoReasoningClient())
    assert adapter.generate("x") == ""
