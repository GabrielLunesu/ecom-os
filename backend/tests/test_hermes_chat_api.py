"""Tests for the Hermes chat HTTP/SSE router (Build Spec Slice 3).

Hermetic: a fresh FastAPI app mounts only this router with dependency overrides for the
bridge (fixture transport) and identity (no real auth/DB). Proves the routes surface the
gateway safely, the health endpoint reports the honest blocked state, and the message stream
emits safe SSE frames.
"""

from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.hermes_chat import get_chat_bridge, get_chat_identity, router
from app.hermes.chat_gateway import ChatIdentity
from app.hermes.fake import FakeHermesTransport


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    bridge = FakeHermesTransport()
    app.dependency_overrides[get_chat_bridge] = lambda: bridge
    app.dependency_overrides[get_chat_identity] = lambda: ChatIdentity(
        ecom_user_id="usr_1", allowed_profile_id="hp_owner"
    )
    return TestClient(app)


def test_health_reports_blocked_on_fixture(client: TestClient) -> None:
    resp = client.get("/hermes/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["conformance_blocked"] is True
    assert set(body["features"].values()) == {"not_ready"}
    # tool-catalog conformance is real evidence and passes even while Hermes is blocked
    assert all(c["passed"] for c in body["conformance"]["tools"])


def test_create_list_history_roundtrip(client: TestClient) -> None:
    created = client.post("/hermes/sessions", json={"title": "t"})
    assert created.status_code == 201
    sid = created.json()["session_id"]

    listed = client.get("/hermes/sessions").json()
    assert sid in {s["session_id"] for s in listed["sessions"]}

    # drive a turn via SSE, then history reflects it
    with client.stream(
        "POST", f"/hermes/sessions/{sid}/messages", json={"text": "hi"}
    ) as stream:
        frames = [line for line in stream.iter_lines() if line]
    assert any("data:" in f for f in frames)

    history = client.get(f"/hermes/sessions/{sid}/history").json()
    assert [m["role"] for m in history["messages"]] == ["user", "assistant"]


def test_status_and_interrupt(client: TestClient) -> None:
    sid = client.post("/hermes/sessions", json={}).json()["session_id"]
    status_body = client.get(f"/hermes/sessions/{sid}/status").json()
    assert status_body["state"] == "idle"
    interrupted = client.post(f"/hermes/sessions/{sid}/interrupt").json()
    assert interrupted["interrupted"] is True


def test_stream_frames_are_safe_events(client: TestClient) -> None:
    sid = client.post("/hermes/sessions", json={}).json()["session_id"]
    with client.stream(
        "POST", f"/hermes/sessions/{sid}/messages", json={"text": "q"}
    ) as stream:
        payloads = []
        for line in stream.iter_lines():
            if line and line.startswith("data:"):
                payloads.append(json.loads(line[len("data:"):].strip()))
    assert payloads, "expected at least one SSE data frame"
    # every frame is the safe projection; no credential keys
    for frame in payloads:
        assert set(frame) == {"type", "seq", "payload"}
        assert "token" not in frame["payload"]
    assert payloads[-1]["type"] == "final"


def test_resume_addresses_existing_session(client: TestClient) -> None:
    sid = client.post("/hermes/sessions", json={}).json()["session_id"]
    resumed = client.post(f"/hermes/sessions/{sid}/resume").json()
    assert resumed["session_id"] == sid
