"""adapters — 타깃 백엔드 (OpenAI 호환 HTTP + Manual). name→class 레지스트리 소유."""

from __future__ import annotations

from redteam.adapters.http_openai import HttpOpenAIAdapter
from redteam.adapters.manual_io import ManualIOAdapter

# 최상위 registry 가 aggregate 하는 name→class 매핑(러너가 인스턴스를 구성).
ADAPTERS: dict[str, type] = {
    "http_openai": HttpOpenAIAdapter,
    "manual": ManualIOAdapter,
}

__all__ = ["ADAPTERS", "HttpOpenAIAdapter", "ManualIOAdapter"]
