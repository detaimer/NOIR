"""run-config 로더 — YAML 읽기 + CLI 오버라이드 병합 + RunConfig 빌드 + api_key_env 해석.

원천은 YAML, CLI 오버라이드가 상위. 순수 스키마/검증은 core.config_schema 가 맡고, 여기서는
파일 I/O·dotted-key 오버라이드·환경변수 해석 같은 경계 작업만 한다. 비밀키는 절대 config 에
인라인하지 않고 `api_key_env`(환경변수 이름)로만 받아 여기서 os.environ 으로 해석한다.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

from redteam.core import ConfigError, EndpointConfig, RunConfig


def read_yaml(path: str | Path) -> dict[str, Any]:
    """YAML 파일을 dict 로 읽는다."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"run-config 파일을 찾을 수 없음: {path}")
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ConfigError(f"run-config 최상위는 매핑이어야 합니다: {path}")
    return data


def apply_overrides(raw: dict[str, Any], overrides: dict[str, Any] | None) -> dict[str, Any]:
    """dotted-key 오버라이드를 깊은 복사본에 적용한다 (예: 'budget.target_calls': 10)."""
    merged = copy.deepcopy(raw)
    for key, value in (overrides or {}).items():
        parts = key.split(".")
        node = merged
        for part in parts[:-1]:
            nxt = node.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                node[part] = nxt
            node = nxt
        node[parts[-1]] = value
    return merged


def load_config(
    path: str | Path,
    overrides: dict[str, Any] | None = None,
    *,
    allow_self_judge: bool = False,
) -> tuple[RunConfig, dict[str, Any]]:
    """YAML+오버라이드를 RunConfig 로 만들고, 스냅샷용 원본 dict 도 함께 돌려준다."""
    raw = apply_overrides(read_yaml(path), overrides)
    cfg = RunConfig.from_dict(raw, allow_self_judge=allow_self_judge)
    return cfg, raw


def resolve_api_key(endpoint: EndpointConfig) -> str | None:
    """엔드포인트의 api_key_env 환경변수를 실제 키로 해석한다 (미설정 이름이면 None)."""
    if not endpoint.api_key_env:
        return None
    value = os.environ.get(endpoint.api_key_env)
    if value is None:
        raise ConfigError(f"환경변수 {endpoint.api_key_env} 가 설정되지 않았습니다")
    return value
