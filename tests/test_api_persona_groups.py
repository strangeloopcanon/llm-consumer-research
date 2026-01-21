"""Tests for persona group listing endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ssr_service.api import app


def test_persona_groups_endpoint_lists_library_groups() -> None:
    client = TestClient(app)
    response = client.get("/persona-groups")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)
    assert payload

    assert any(group["name"] == "us_toothpaste_buyers" for group in payload)
    first = payload[0]
    assert "persona_count" in first
