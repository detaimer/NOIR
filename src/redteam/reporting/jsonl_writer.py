"""실행 산출물 기록 — attempts.jsonl + summary.json + config.snapshot.yaml(redacted).

I/O 경계 모듈. 순수 집계는 aggregate 에 두고 여기서는 직렬화·파일 쓰기만 한다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path

import yaml

from redteam.core import Attempt
from redteam.reporting.aggregate import Summary

# 값을 마스킹할 민감 키 부분문자열(대소문자 무시). "*_env" 는 env-var 이름만 담으므로 제외.
_SECRET_KEY_PATTERNS = ("api_key", "apikey", "token", "secret", "password")
_REDACTED = "***"


def _json_default(obj: object):
    """json 기본 인코더가 모르는 값 처리 — Enum→value, dataclass→dict."""
    if isinstance(obj, Enum):
        return obj.value
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    raise TypeError(f"직렬화 불가 타입: {type(obj).__name__}")


def _is_secret_key(key: str) -> bool:
    """민감 키 여부 — 패턴 포함 && '_env' 접미(이름 홀더)가 아님."""
    kl = key.lower()
    if kl.endswith("_env"):
        return False
    return any(pat in kl for pat in _SECRET_KEY_PATTERNS)


def _redact(obj: object) -> object:
    """config 를 재귀적으로 복사하며 민감 키의 값을 '***' 로 치환(원본 불변)."""
    if isinstance(obj, dict):
        return {k: (_REDACTED if _is_secret_key(str(k)) else _redact(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_redact(v) for v in obj]
    return obj


def _attempt_to_dict(attempt: Attempt) -> dict:
    """Attempt → JSON 직렬화 가능한 dict (중첩 dataclass·tuple 재귀 변환)."""
    return asdict(attempt)


def write_run(
    out_dir: str | Path,
    attempts: list[Attempt],
    summary: Summary,
    config: dict,
) -> dict[str, Path]:
    """out_dir 에 attempts.jsonl·summary.json·config.snapshot.yaml(redacted) 를 쓴다."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    attempts_path = out / "attempts.jsonl"
    with attempts_path.open("w", encoding="utf-8") as fh:
        for attempt in attempts:
            fh.write(
                json.dumps(_attempt_to_dict(attempt), default=_json_default, ensure_ascii=False)
            )
            fh.write("\n")

    summary_path = out / "summary.json"
    summary_path.write_text(
        json.dumps(asdict(summary), default=_json_default, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    config_path = out / "config.snapshot.yaml"
    config_path.write_text(
        yaml.safe_dump(_redact(config), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    return {"attempts": attempts_path, "summary": summary_path, "config": config_path}
