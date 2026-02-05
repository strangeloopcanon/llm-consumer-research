"""Tests for AppSettings parsing behavior."""

from ssr_service.config import AppSettings


def test_cors_allow_origins_parses_single_origin_from_env(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://llm-consumer-research-ui.onrender.com",
    )

    settings = AppSettings()

    assert settings.cors_allow_origins == [
        "https://llm-consumer-research-ui.onrender.com"
    ]


def test_cors_allow_origins_parses_comma_separated_origins(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "https://a.example, https://b.example,https://c.example",
    )

    settings = AppSettings()

    assert settings.cors_allow_origins == [
        "https://a.example",
        "https://b.example",
        "https://c.example",
    ]
