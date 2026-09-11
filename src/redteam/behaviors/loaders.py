"""behaviors 로더 — 소스 문자열을 Behavior 리스트로 디스패치하고 domain/limit 필터를 적용한다.

지원 소스: `builtin`(내장 팩), `<path>.jsonl`(사용자 파일). `jbb`/`harmbench` 는 M13 예정 —
현재는 ConfigError. jsonl 각 줄은 {id, prompt, domain} 필수 + {subcat, tags, source} 선택.
"""

from __future__ import annotations

import json
from pathlib import Path

from redteam.behaviors.builtin_seed import builtin_behaviors
from redteam.core import Behavior, BehaviorSpec, ConfigError

_DEFERRED = {"jbb", "harmbench"}


def _behavior_from_row(row: dict, default_source: str) -> Behavior:
    try:
        return Behavior(
            id=row["id"],
            prompt=row["prompt"],
            domain=row["domain"],
            subcat=row.get("subcat", ""),
            tags=tuple(row.get("tags", ())),
            source=row.get("source", default_source),
        )
    except KeyError as e:
        raise ConfigError(f"jsonl behavior 행에 {e} 누락: {row!r}") from e


def _load_jsonl(path: Path) -> list[Behavior]:
    out: list[Behavior] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                raise ConfigError(f"{path} JSON 파싱 실패: {e}") from e
            out.append(_behavior_from_row(row, default_source=path.stem))
    return out


def load_behaviors(spec: BehaviorSpec) -> list[Behavior]:
    """BehaviorSpec 을 해석해 필터링된 Behavior 리스트를 반환한다."""
    source = spec.source
    if source == "builtin":
        behaviors = builtin_behaviors()
    elif source.endswith(".jsonl"):
        path = Path(source)
        if not path.exists():
            raise ConfigError(f"behaviors 파일을 찾을 수 없음: {source}")
        behaviors = _load_jsonl(path)
    elif source in _DEFERRED:
        raise ConfigError(f"behaviors 소스 '{source}' 는 아직 미지원(M13 예정)")
    else:
        raise ConfigError(f"알 수 없는 behaviors 소스 '{source}'. 사용: builtin | <path>.jsonl")

    if spec.domain is not None:
        behaviors = [b for b in behaviors if b.domain == spec.domain]
    if spec.limit is not None:
        behaviors = behaviors[: spec.limit]
    return behaviors
