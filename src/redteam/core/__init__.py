"""core — 플러그인 계약(ABC/Protocol)·레코드 타입·예산·설정 스키마·도메인 예외.

역할 패키지(probes/adapters/detectors/reporting/behaviors)는 오직 이 패키지에만 의존한다.
"""

from redteam.core.budget import BudgetedTarget, CallCounter
from redteam.core.config_schema import (
    BehaviorSpec,
    DetectorSpec,
    EndpointConfig,
    RunConfig,
    TechniqueSpec,
)
from redteam.core.errors import (
    AdapterError,
    BudgetExceeded,
    ConfigError,
    RedteamError,
    UnknownComponent,
)
from redteam.core.interfaces import Adapter, Detector, Probe, ProbeContext
from redteam.core.records import (
    Attempt,
    Behavior,
    DetectionResult,
    Message,
    Role,
    Turn,
)

__all__ = [
    # interfaces
    "Adapter",
    "Detector",
    "Probe",
    "ProbeContext",
    # records
    "Attempt",
    "Behavior",
    "DetectionResult",
    "Message",
    "Role",
    "Turn",
    # budget
    "BudgetedTarget",
    "CallCounter",
    # config
    "BehaviorSpec",
    "DetectorSpec",
    "EndpointConfig",
    "RunConfig",
    "TechniqueSpec",
    # errors
    "AdapterError",
    "BudgetExceeded",
    "ConfigError",
    "RedteamError",
    "UnknownComponent",
]
