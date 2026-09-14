"""실 엔드포인트 스모크 — 기본 실행에서 제외(`pytest -m live` 로만).

네트워크·비용이 드는 유일한 테스트 묶음이다. 다음 환경변수로 대상을 지정한다:

  RT_LIVE_BASE_URL   OpenAI 호환 엔드포인트 (예: http://localhost:11434/v1)
  RT_LIVE_MODEL      모델 이름 (예: llama3.1:8b)
  RT_LIVE_API_KEY_ENV  API 키가 담긴 **다른** 환경변수의 이름 (로컬 서버면 생략 가능)

미설정 시 skip 하므로 `pytest -m live` 를 그냥 돌려도 실패하지 않는다.
프롬프트는 전부 무해한 스모크용이며 공격 기법을 실행하지 않는다.
"""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.live

live = pytest.importorskip("redteam.adapters.http_openai")

from redteam.core import AdapterError, Message, Role  # noqa: E402

_BASE_URL = "RT_LIVE_BASE_URL"
_MODEL = "RT_LIVE_MODEL"
_API_KEY_ENV = "RT_LIVE_API_KEY_ENV"


def _endpoint() -> tuple[str, str, str]:
    """환경변수에서 (base_url, model, api_key) 를 읽는다 (미설정 → skip)."""
    base_url = os.environ.get(_BASE_URL)
    model = os.environ.get(_MODEL)
    if not base_url or not model:
        pytest.skip(f"{_BASE_URL}/{_MODEL} 미설정 — live 스모크 건너뜀")

    key_env = os.environ.get(_API_KEY_ENV)
    api_key = os.environ.get(key_env) if key_env else None
    if key_env and not api_key:
        pytest.skip(f"{_API_KEY_ENV}={key_env} 가 가리키는 환경변수가 비어 있음")

    # 로컬 서버(Ollama/vLLM 등)는 키를 검사하지 않지만 openai 클라이언트가 값을 요구한다.
    return base_url, model, api_key or "not-needed"


@pytest.fixture(scope="module")
def endpoint() -> tuple[str, str, str]:
    return _endpoint()


@pytest.fixture(scope="module")
def adapter(endpoint):
    base_url, model, api_key = endpoint
    return live.HttpOpenAIAdapter(model=model, base_url=base_url, api_key=api_key)


def test_generate_roundtrip(adapter):
    out = adapter.generate("Reply with the single word: pong", system="You are terse.")
    assert isinstance(out, str)
    assert out.strip()


def test_chat_roundtrip(adapter):
    out = adapter.chat(
        [
            Message(role=Role.SYSTEM, content="You are terse."),
            Message(role=Role.USER, content="Name one primary color. One word."),
        ]
    )
    assert isinstance(out, str)
    assert out.strip()


def test_unknown_model_raises_adapter_error(endpoint):
    """오류는 raw 예외가 아니라 AdapterError 로 래핑되어 올라온다(runner 가 흡수하는 계약)."""
    base_url, _model, api_key = endpoint
    broken = live.HttpOpenAIAdapter(
        model="definitely-not-a-real-model-xyz",
        base_url=base_url,
        api_key=api_key,
    )
    with pytest.raises(AdapterError):
        broken.generate("hi")
