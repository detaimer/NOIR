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
        return _FakeResponse(self._outer.reply)


class _FakeChat:
    def __init__(self, outer: _FakeClient) -> None:
        self.completions = _FakeCompletions(outer)


class _FakeClient:
    """choices[0].message.content 를 돌려주는 최소 stub 클라이언트."""

    def __init__(self, reply: str = "FAKE_REPLY") -> None:
        self.reply = reply
        self.calls: list[dict] = []
        self.chat = _FakeChat(self)


class _FakeMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeChoice(content)]


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
