"""도메인 예외 — 모든 예외는 `RedteamError` 를 상속한다 (광범위 except 대신 계층 포착)."""

from __future__ import annotations


class RedteamError(Exception):
    """redteam 도메인 예외의 공통 기반."""


class ConfigError(RedteamError):
    """run-config 가 유효하지 않을 때 (예: target == judge)."""


class AdapterError(RedteamError):
    """타깃/judge 엔드포인트 호출이 실패했을 때 (네트워크·HTTP·파싱)."""


class BudgetExceeded(RedteamError):
    """Fair-ASR 타깃-호출 예산 B 를 초과했을 때 (BudgetedTarget 가 raise)."""

    def __init__(self, limit: int, message: str | None = None) -> None:
        self.limit = limit
        super().__init__(message or f"타깃 호출 예산 {limit} 초과")


class UnknownComponent(RedteamError):
    """레지스트리에서 알 수 없는 이름을 조회했을 때 — 유효 목록을 제시한다."""

    def __init__(self, role: str, name: str, available: tuple[str, ...]) -> None:
        self.role = role
        self.name = name
        self.available = tuple(available)
        valid = ", ".join(self.available) if self.available else "(없음)"
        super().__init__(f"알 수 없는 {role} '{name}'. 사용 가능: {valid}")
