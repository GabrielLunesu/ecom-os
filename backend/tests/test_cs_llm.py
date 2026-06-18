"""CS LLM backend routing: Hermes gateway (no Anthropic key) vs direct Anthropic."""

from __future__ import annotations

from typing import Any

import pytest

from app.services import cs_llm


def _no_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(settings, "anthropic_api_key", "", raising=False)


class _FakeResp:
    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": "Hi there!"}]}


@pytest.mark.asyncio
async def test_routes_through_hermes_gateway_without_anthropic_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _no_anthropic(monkeypatch)
    monkeypatch.setenv("HERMES_GATEWAY_URL", "https://hermes.example")
    assert cs_llm._llm_available() is True  # gateway counts as a backend

    captured: dict[str, Any] = {}

    class FakeClient:
        def __init__(self, **kw: Any) -> None:
            captured["base_url"] = kw.get("base_url")

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *a: object) -> None:
            pass

        async def post(self, path: str, *, headers: Any = None, json: Any = None) -> _FakeResp:
            captured["path"] = path
            captured["json"] = json
            return _FakeResp()

    monkeypatch.setattr(cs_llm.httpx, "AsyncClient", FakeClient)

    out = await cs_llm.generate_email(
        prompt="reassure them", context={}, history=[], support_name="Support", public_url=""
    )
    assert out == "Hi there!"
    # Delegated to the Hermes cs subagent — not the Anthropic API.
    assert captured["base_url"] == "https://hermes.example"
    assert captured["path"] == "/delegate"
    assert captured["json"]["profile"] == "cs"


@pytest.mark.asyncio
async def test_no_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    _no_anthropic(monkeypatch)
    monkeypatch.delenv("HERMES_GATEWAY_URL", raising=False)
    monkeypatch.setattr(settings, "hermes_gateway_url", "", raising=False)
    assert cs_llm._llm_available() is False
    with pytest.raises(RuntimeError):
        await cs_llm.generate_email(
            prompt="x", context={}, history=[], support_name="S", public_url=""
        )
