"""A01 foundation: secret redaction at log + error boundaries; detection corpus.

Backs the §12.2 invariant "no secret appears in logs, traces, API responses, or tool
output" with a detection corpus (05-OPS §4.2).
"""

from __future__ import annotations

import json
import logging

import pytest

from app.core.errors import ApiError, ErrorCode
from app.core.logging import JsonFormatter, KeyValueFormatter
from app.core.redaction import (
    REDACTED,
    is_sensitive_key,
    redact_mapping,
    scan_for_secrets,
)

SHOPIFY_SECRET = "shpat_" + ("0123456789abcdef" * 2)
ANTHROPIC_SECRET = "sk-ant-" + "api03-abcdef0123456789abcdef0123"
BEARER = "Bearer " + "eyJhbGciOiJIUzI1Niastufffffffff"
PBKDF2 = "pbkdf2_sha256" + "$200000$c2FsdHNhbHQ$ZGlnZXN0ZGlnZXN0"


class TestRedactionPrimitive:
    @pytest.mark.parametrize(
        "key",
        ["password", "api_key", "Authorization", "access_token", "client_secret", "verifier"],
    )
    def test_sensitive_keys(self, key: str) -> None:
        assert is_sensitive_key(key)

    @pytest.mark.parametrize("key", ["token_selector", "request_id", "trace_id", "user_id", "name"])
    def test_safe_keys(self, key: str) -> None:
        assert not is_sensitive_key(key)

    def test_redact_mapping_nested(self) -> None:
        data = {
            "user_id": "u1",
            "authorization": BEARER,
            "nested": {"api_key": SHOPIFY_SECRET, "ok": "value"},
        }
        out = redact_mapping(data)
        assert out["user_id"] == "u1"
        assert out["authorization"] == REDACTED
        assert out["nested"]["api_key"] == REDACTED
        assert out["nested"]["ok"] == "value"

    def test_scan_detects_known_secret_formats(self) -> None:
        for secret in (SHOPIFY_SECRET, ANTHROPIC_SECRET, BEARER, PBKDF2):
            assert scan_for_secrets(f"leak: {secret}"), secret

    def test_scan_clean_text(self) -> None:
        assert scan_for_secrets("nothing secret here, id=abc123") == []


def _record(extra: dict) -> logging.LogRecord:
    record = logging.LogRecord(
        name="t",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="event",
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestLoggingRedaction:
    def test_json_formatter_redacts_extras(self) -> None:
        out = JsonFormatter().format(_record({"api_key": SHOPIFY_SECRET, "user_id": "u1"}))
        payload = json.loads(out)
        assert payload["api_key"] == REDACTED
        assert payload["user_id"] == "u1"
        assert not scan_for_secrets(out)

    def test_keyvalue_formatter_redacts_extras(self) -> None:
        fmt = KeyValueFormatter("%(message)s")
        out = fmt.format(_record({"authorization": BEARER}))
        assert REDACTED in out
        assert not scan_for_secrets(out)


@pytest.mark.asyncio
async def test_api_error_details_redacted_in_response() -> None:
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from app.core.error_handling import install_error_handling

    app = FastAPI()
    install_error_handling(app)

    @app.get("/boom")
    async def boom() -> None:
        # A handler that mistakenly puts a secret in details must not leak it.
        raise ApiError(
            ErrorCode.FORBIDDEN,
            "denied",
            details={"api_key": SHOPIFY_SECRET, "store_id": "s1"},
        )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        resp = await client.get("/boom")
    assert resp.status_code == 403
    body = resp.json()
    assert body["details"]["api_key"] == REDACTED
    assert body["details"]["store_id"] == "s1"
    assert not scan_for_secrets(resp.text)
