"""behaviors 로더 — 소스 문자열을 Behavior 리스트로 디스패치하고 domain/limit 필터를 적용한다.

지원 소스:
  - `builtin`             내장 팩
  - `<path>.jsonl`        사용자 파일 ({id, prompt, domain} 필수 + {subcat, tags, source} 선택)
  - `jbb` / `harmbench`   공개 벤치마크. **로컬 파일만** 읽는다(`path` 필수, 다운로드 없음) —
                          데이터셋 라이선스·수집 경로를 사용자가 통제하게 하기 위함.

외부 셋은 원본 taxonomy 를 버리지 않는다: 대응되는 내부 도메인이 있으면 매핑하고, 없으면 슬러그로
보존하며, 원본 카테고리/태그는 언제나 `tags` 에 접두사와 함께 남긴다(`docs/evaluation.md`).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from redteam.behaviors.builtin_seed import builtin_behaviors
from redteam.core import Behavior, BehaviorSpec, ConfigError

_EXTERNAL = ("jbb", "harmbench")

# 외부 카테고리 → 내부 도메인. 여기 없는 값은 슬러그를 그대로 도메인으로 쓴다.
_JBB_DOMAINS = {
    "malware_hacking": "cyber",
    "privacy": "privacy",
    "disinformation": "misinfo",
    "fraud_deception": "fraud",
    "economic_harm": "fraud",
}
_HARMBENCH_DOMAINS = {
    "cybercrime_intrusion": "cyber",
    "chemical_biological": "cbrn",
    "misinformation_disinformation": "misinfo",
    "illegal": "illegal_goods",
}


def _slug(value: str) -> str:
    """자유 텍스트 카테고리 → 도메인 슬러그 (소문자·비영숫자는 '_' 로)."""
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", value.strip().lower())).strip("_")


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


def _read_rows(path: Path) -> list[dict[str, Any]]:
    """CSV/JSON/JSONL 을 공통 '행 dict 리스트' 로 읽는다 (키는 소문자 정규화)."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            with path.open(encoding="utf-8", newline="") as f:
                raw = list(csv.DictReader(f))
        elif suffix == ".jsonl":
            raw = [
                json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()
            ]
        else:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            raw = loaded if isinstance(loaded, list) else loaded.get("data", [])
    except (json.JSONDecodeError, csv.Error, UnicodeDecodeError) as e:
        raise ConfigError(f"{path} 파싱 실패: {e}") from e
    return [{str(k).strip().lower(): v for k, v in row.items() if k is not None} for row in raw]


def _required(row: dict, key: str, path: Path, line: int) -> str:
    value = row.get(key)
    if value is None or str(value).strip() == "":
        raise ConfigError(
            f"{path}:{line} 에 '{key}' 컬럼이 없거나 비어 있습니다 (컬럼: {sorted(row)})"
        )
    return str(value).strip()


def _load_jbb(path: Path) -> list[Behavior]:
    """JailbreakBench(JBB-Behaviors) — 컬럼: Index, Goal, Target, Behavior, Category, Source."""
    out: list[Behavior] = []
    for i, row in enumerate(_read_rows(path), start=1):
        goal = _required(row, "goal", path, i)
        category = str(row.get("category", "") or "").strip()
        index = str(row.get("index", "") or i - 1).strip()
        origin = str(row.get("source", "") or "").strip()
        tags = [f"jbb:category:{category}"] if category else []
        if origin:
            tags.append(f"jbb:source:{origin}")
        slug = _slug(category) if category else "unknown"
        out.append(
            Behavior(
                id=f"jbb_{index}",
                prompt=goal,
                domain=_JBB_DOMAINS.get(slug, slug),
                subcat=str(row.get("behavior", "") or "").strip(),
                tags=tuple(tags),
                source="jbb",
            )
        )
    return out


def _load_harmbench(path: Path) -> list[Behavior]:
    """HarmBench — 컬럼: Behavior, FunctionalCategory, SemanticCategory, Tags,
    ContextString, BehaviorID.

    `contextual` behavior 는 ContextString 이 과제의 일부이므로 프롬프트 앞에 붙인다.
    """
    out: list[Behavior] = []
    for i, row in enumerate(_read_rows(path), start=1):
        behavior = _required(row, "behavior", path, i)
        functional = str(row.get("functionalcategory", "") or "").strip()
        semantic = str(row.get("semanticcategory", "") or "").strip()
        context = str(row.get("contextstring", "") or "").strip()
        bid = str(row.get("behaviorid", "") or f"harmbench_{i}").strip()

        tags = []
        if functional:
            tags.append(f"harmbench:functional:{functional}")
        if semantic:
            tags.append(f"harmbench:semantic:{semantic}")
        tags += [
            f"harmbench:tag:{t.strip()}"
            for t in str(row.get("tags", "") or "").split(",")
            if t.strip()
        ]

        slug = _slug(semantic) if semantic else "unknown"
        out.append(
            Behavior(
                id=bid,
                prompt=f"{context}\n\n{behavior}" if context else behavior,
                domain=_HARMBENCH_DOMAINS.get(slug, slug),
                subcat=semantic,
                tags=tuple(tags),
                source="harmbench",
            )
        )
    return out


_EXTERNAL_LOADERS = {"jbb": _load_jbb, "harmbench": _load_harmbench}


def _load_external(source: str, spec: BehaviorSpec) -> list[Behavior]:
    """jbb/harmbench 를 로컬 파일에서 읽는다 (경로 미지정/부재는 ConfigError)."""
    if not spec.path:
        raise ConfigError(
            f"behaviors 소스 '{source}' 는 로컬 파일이 필요합니다 — "
            f"내려받은 뒤 behaviors.path 로 경로를 지정하세요 (자동 다운로드하지 않습니다)."
        )
    path = Path(spec.path)
    if not path.exists():
        raise ConfigError(f"behaviors 파일을 찾을 수 없음: {spec.path}")
    return _EXTERNAL_LOADERS[source](path)


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
    elif source in _EXTERNAL:
        behaviors = _load_external(source, spec)
    else:
        raise ConfigError(
            f"알 수 없는 behaviors 소스 '{source}'. 사용: builtin | jbb | harmbench | <path>.jsonl"
        )

    if spec.domain is not None:
        behaviors = [b for b in behaviors if b.domain == spec.domain]
    if spec.limit is not None:
        behaviors = behaviors[: spec.limit]
    return behaviors
