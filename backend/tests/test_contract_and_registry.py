"""A01 foundation: router-registration convention + generated-contract guards.

Guards that the foundation contracts are present and strict in the OpenAPI schema (the
source orval turns into TypeScript), without requiring Node in CI.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.registry import DOMAIN_ROUTERS, register_domain_routers
from app.core.errors import ErrorCode


def test_register_domain_routers_mounts_foundation_routes() -> None:
    parent = APIRouter()
    register_domain_routers(parent)
    paths = {route.path for route in parent.routes}  # type: ignore[attr-defined]
    assert "/identity/me" in paths
    assert "/identity/owner-bootstrap" in paths
    assert "/auth/bootstrap" in paths


def test_registry_has_no_duplicate_routers() -> None:
    assert len(DOMAIN_ROUTERS) == len(set(id(r) for r in DOMAIN_ROUTERS))


class TestOpenApiContract:
    def _schema(self) -> dict:
        from app.main import app

        return app.openapi()

    def test_foundation_schemas_present(self) -> None:
        schemas = self._schema()["components"]["schemas"]
        for name in (
            "ErrorEnvelope",
            "ErrorCode",
            "ActorView",
            "BootstrapStatus",
            "OwnerClaimResult",
            "HealthReportResponse",
            "ComponentHealthModel",
        ):
            assert name in schemas, name

    def test_error_code_enum_has_fifteen_values(self) -> None:
        schemas = self._schema()["components"]["schemas"]
        enum_values = set(schemas["ErrorCode"]["enum"])
        assert enum_values == {c.value for c in ErrorCode}

    def test_error_envelope_is_strict(self) -> None:
        env = self._schema()["components"]["schemas"]["ErrorEnvelope"]
        # Required typed fields => strict TS (no loose/any contract).
        assert set(env["required"]) >= {"detail", "code", "retryable"}
        assert env["properties"]["code"]["$ref"].endswith("/ErrorCode")

    def test_identity_me_documents_typed_errors(self) -> None:
        schema = self._schema()
        responses = schema["paths"]["/api/v1/identity/me"]["get"]["responses"]
        assert "401" in responses
        ref = responses["401"]["content"]["application/json"]["schema"]["$ref"]
        assert ref.endswith("/ErrorEnvelope")
