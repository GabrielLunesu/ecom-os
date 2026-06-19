"""Central domain-router registration.

Registration convention (A01-owned, per parallel-build FILE-OWNERSHIP):

1. Each domain exposes ``router = APIRouter(prefix=..., tags=[...])`` from its
   ``app/api/<domain>.py`` module — it never edits central wiring itself.
2. A domain is mounted by adding it to :data:`DOMAIN_ROUTERS` here. Other agents request
   that one-line registration via the interface queue; A01 (and A09 at integration)
   applies it. This keeps ``main.py`` free of churn and gives one obvious mount point.
3. Routers are versioned under the ``/api/v1`` parent in :func:`register_domain_routers`.

Health/liveness probes are mounted directly on the app (unversioned) in ``main.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api.activity import router as activity_router
from app.api.agent import router as agent_router
from app.api.agents import router as agents_router
from app.api.approvals import router as approvals_router
from app.api.auth import router as auth_router
from app.api.board_group_memory import router as board_group_memory_router
from app.api.board_groups import router as board_groups_router
from app.api.board_memory import router as board_memory_router
from app.api.board_onboarding import router as board_onboarding_router
from app.api.board_webhooks import router as board_webhooks_router
from app.api.boards import router as boards_router
from app.api.ecom import router as ecom_router
from app.api.ecom_webhooks import router as ecom_webhooks_router
from app.api.gateway import router as gateway_router
from app.api.gateways import router as gateways_router
from app.api.identity import router as identity_router
from app.api.metrics import router as metrics_router
from app.api.organizations import router as organizations_router
from app.api.skills_marketplace import router as skills_marketplace_router
from app.api.souls_directory import router as souls_directory_router
from app.api.tags import router as tags_router
from app.api.task_custom_fields import router as task_custom_fields_router
from app.api.tasks import router as tasks_router
from app.api.users import router as users_router

if TYPE_CHECKING:
    from fastapi import APIRouter

__all__ = ["DOMAIN_ROUTERS", "register_domain_routers"]

# Order is mostly cosmetic (OpenAPI/tag grouping). A01 foundation routes come first.
DOMAIN_ROUTERS: list[APIRouter] = [
    auth_router,
    identity_router,
    agent_router,
    agents_router,
    activity_router,
    gateway_router,
    gateways_router,
    metrics_router,
    organizations_router,
    souls_directory_router,
    skills_marketplace_router,
    board_groups_router,
    board_group_memory_router,
    boards_router,
    board_memory_router,
    board_webhooks_router,
    board_onboarding_router,
    approvals_router,
    tasks_router,
    task_custom_fields_router,
    tags_router,
    users_router,
    ecom_router,
    ecom_webhooks_router,
]


def register_domain_routers(parent: APIRouter) -> None:
    """Mount every registered domain router on the versioned ``parent`` router."""
    for router in DOMAIN_ROUTERS:
        parent.include_router(router)
