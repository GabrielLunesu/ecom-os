"""HermesBridge — Ecom-OS's normalized boundary to Hermes (Runtime Spec §2.2).

Hermes stays an independent peer: this package speaks only supported protocols, never
writes Hermes private state, and never forks/patches Hermes (AGENTS I-01/I-04). Domain code
uses ``HermesBridge``; it does not speak raw Hermes transport methods directly (AGENTS §3).

Until a real Hermes release is pinned and probed, the bridge is exercised through
``FakeHermesTransport`` + conformance fixtures (Operating Protocol §7, AGENTS I-19). No
feature reaches ``ready`` on the fake.
"""

from __future__ import annotations

from .bridge import HermesBridge
from .capabilities import (
    FEATURE_REQUIREMENTS,
    REQUIRED_FLAGS,
    CompatibilityRecord,
    FeatureReadiness,
    evaluate_feature,
)
from .channels import (
    ChannelDeliveryService,
    DeliveryIntent,
    DeliveryReceipt,
    DeliveryStatus,
    SchedulePort,
)
from .chat_gateway import (
    ALLOWED_COMMANDS,
    BrowserCommandDenied,
    ChatIdentity,
    ChatSessionGateway,
)
from .conformance import ConformanceReport, run_conformance_suite
from .health import hermes_health_snapshot
from .native import (
    HermesNativeConfig,
    HermesNativeNotConfigured,
    HermesNativeNotImplemented,
    HermesNativeTransport,
)
from .runs import BackgroundRunPort, RunLeaseError

# NOTE: OpenClawCompatTransport is intentionally NOT re-exported here. It is a dev/compat
# transport that imports the legacy OpenClaw stack (and runtime settings); importing it
# eagerly would couple the whole hermes package to that config. Import it directly from
# ``app.hermes.openclaw_compat`` where needed.
from .types import (
    BackgroundRunRequest,
    CreateSession,
    HermesCapabilities,
    HermesEvent,
    HermesEventType,
    HermesHealth,
    HermesHistory,
    HermesRunRef,
    HermesRunStatus,
    HermesSessionRef,
    HermesSessionStatus,
    HermesSessionSummary,
    InteractivePrompt,
)

__all__ = [
    "HermesBridge",
    "FEATURE_REQUIREMENTS",
    "REQUIRED_FLAGS",
    "CompatibilityRecord",
    "FeatureReadiness",
    "evaluate_feature",
    "BackgroundRunRequest",
    "CreateSession",
    "HermesCapabilities",
    "HermesEvent",
    "HermesEventType",
    "HermesHealth",
    "HermesHistory",
    "HermesRunRef",
    "HermesRunStatus",
    "HermesSessionRef",
    "HermesSessionStatus",
    "HermesSessionSummary",
    "InteractivePrompt",
    "ChannelDeliveryService",
    "DeliveryIntent",
    "DeliveryReceipt",
    "DeliveryStatus",
    "SchedulePort",
    "ConformanceReport",
    "run_conformance_suite",
    "hermes_health_snapshot",
    "HermesNativeConfig",
    "HermesNativeNotConfigured",
    "HermesNativeNotImplemented",
    "HermesNativeTransport",
    "BackgroundRunPort",
    "RunLeaseError",
    "ALLOWED_COMMANDS",
    "BrowserCommandDenied",
    "ChatIdentity",
    "ChatSessionGateway",
]
