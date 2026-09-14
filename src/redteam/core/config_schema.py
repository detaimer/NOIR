"""run-config 스키마 — 순수 파싱/검증 (I/O·환경변수 해석 없음).

YAML 로드와 CLI 오버라이드·api_key_env 해석은 config_loader(M8)가 담당하고,
여기서는 dict → RunConfig 변환과 불변식(target ≠ judge 엔드포인트) 검증만 한다.

설계 결정(E): target/attacker/judge 는 각각 독립 **엔드포인트**이고, 실행할 판정기 목록은
별도 `detectors`(primary first). LLM 기반 detector(llama_guard/strong_reject)는 judge 엔드포인트를
사용한다. target 과 judge 엔드포인트가 같으면(자기 채점) ConfigError — `allow_self_judge` 로만 허용.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from redteam.core.errors import ConfigError


@dataclass(frozen=True)
class EndpointConfig:
    """OpenAI 호환 엔드포인트 하나 (상업 API/로컬 서버 공통)."""

    base_url: str
    model: str
    api_key_env: str | None = None
    name: str = ""
    adapter: str = "http_openai"

    def identity(self) -> tuple[str, str]:
        """자기 채점 판정용 동일성 키 (base_url, model)."""
        return (self.base_url, self.model)

    @classmethod
    def from_dict(cls, d: dict[str, Any], *, name: str = "") -> EndpointConfig:
        if not isinstance(d, dict):
            raise ConfigError(f"엔드포인트 '{name}' 설정은 매핑이어야 합니다")
        try:
            base_url = d["base_url"]
            model = d["model"]
        except KeyError as e:
            raise ConfigError(f"엔드포인트 '{name}' 에 {e} 누락") from e
        return cls(
            base_url=base_url,
            model=model,
            api_key_env=d.get("api_key_env"),
            name=d.get("name", name),
            adapter=d.get("adapter", "http_openai"),
        )


@dataclass(frozen=True)
class DetectorSpec:
    """실행할 판정기 하나 — 이름 + 생성 파라미터."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BehaviorSpec:
    """behaviors 소스 + 필터.

    `path` 는 외부 셋(jbb/harmbench)의 **로컬 파일** 경로 — 네트워크 다운로드는 하지 않는다.
    """

    source: str
    domain: str | None = None
    limit: int | None = None
    path: str | None = None

    @classmethod
    def from_config(cls, value: Any) -> BehaviorSpec:
        if isinstance(value, str):
            return cls(source=value)
        if isinstance(value, dict):
            if "source" not in value:
                raise ConfigError("behaviors 설정에 'source' 누락")
            return cls(
                source=value["source"],
                domain=value.get("domain"),
                limit=value.get("limit"),
                path=value.get("path"),
            )
        raise ConfigError("behaviors 는 문자열 또는 매핑이어야 합니다")


def _parse_detector(entry: Any) -> DetectorSpec:
    if isinstance(entry, str):
        return DetectorSpec(name=entry)
    if isinstance(entry, dict) and len(entry) == 1:
        name = next(iter(entry))
        params = entry[name] or {}
        if not isinstance(params, dict):
            raise ConfigError(f"detector '{name}' 파라미터는 매핑이어야 합니다")
        return DetectorSpec(name=name, params=dict(params))
    raise ConfigError(f"detector 항목 형식 오류: {entry!r}")


@dataclass(frozen=True)
class TechniqueSpec:
    """실행할 공격 기법 하나 — 이름 + 기법별 파라미터(DetectorSpec 과 동일한 형태)."""

    name: str
    params: dict[str, Any] = field(default_factory=dict)


def _parse_technique(entry: Any) -> TechniqueSpec:
    if isinstance(entry, str):
        return TechniqueSpec(name=entry)
    if isinstance(entry, dict) and len(entry) == 1:
        name = next(iter(entry))
        params = entry[name] or {}
        if not isinstance(params, dict):
            raise ConfigError(f"technique '{name}' 파라미터는 매핑이어야 합니다")
        return TechniqueSpec(name=name, params=dict(params))
    raise ConfigError(f"technique 항목 형식 오류: {entry!r}")


@dataclass(frozen=True)
class RunConfig:
    """한 번의 `rt run` 실행 설정 (검증 완료된 불변 값)."""

    target: EndpointConfig
    detectors: tuple[DetectorSpec, ...]
    techniques: tuple[TechniqueSpec, ...]
    behaviors: BehaviorSpec
    budget: int
    judge: EndpointConfig | None = None
    attacker: EndpointConfig | None = None
    out_dir: str = "out/runs"
    html: bool = True
    allow_self_judge: bool = False

    @classmethod
    def from_dict(cls, d: dict[str, Any], *, allow_self_judge: bool = False) -> RunConfig:
        if "target" not in d:
            raise ConfigError("run-config 에 'target' 엔드포인트 누락")
        target = EndpointConfig.from_dict(d["target"], name="target")
        judge = EndpointConfig.from_dict(d["judge"], name="judge") if d.get("judge") else None
        attacker = (
            EndpointConfig.from_dict(d["attacker"], name="attacker") if d.get("attacker") else None
        )

        if judge is not None and judge.identity() == target.identity() and not allow_self_judge:
            raise ConfigError(
                "target 과 judge 엔드포인트가 동일합니다(자기 채점). "
                "allow_self_judge 로만 허용됩니다."
            )

        detectors = tuple(_parse_detector(e) for e in d.get("detectors", []))
        techniques = tuple(_parse_technique(e) for e in d.get("techniques", []))
        behaviors = BehaviorSpec.from_config(d.get("behaviors", "builtin"))
        reporting = d.get("reporting", {}) or {}
        budget_cfg = d.get("budget", {}) or {}

        return cls(
            target=target,
            detectors=detectors,
            techniques=techniques,
            behaviors=behaviors,
            budget=int(budget_cfg.get("target_calls", 0)),
            judge=judge,
            attacker=attacker,
            out_dir=d.get("out_dir", "out/runs"),
            html=bool(reporting.get("html", True)),
            allow_self_judge=allow_self_judge,
        )
