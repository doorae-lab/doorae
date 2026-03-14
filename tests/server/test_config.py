"""서버 설정 테스트."""

import os
import pytest
from doorae.server.config import ServerSettings, get_server_settings


def test_server_settings_defaults():
    """기본값 테스트."""
    settings = ServerSettings()
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert settings.max_rooms == 100


def test_server_settings_from_env(monkeypatch):
    """환경변수 로드 테스트."""
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "9000")
    monkeypatch.setenv("SERVER_MAX_ROOMS", "50")

    settings = ServerSettings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000
    assert settings.max_rooms == 50


def test_server_settings_env_prefix_isolation(monkeypatch):
    """PREFIX 격리 테스트."""
    # 다른 PREFIX는 무시되어야 함
    monkeypatch.setenv("HOST", "wrong.host")
    monkeypatch.setenv("PORT", "9999")
    monkeypatch.setenv("SERVER_HOST", "127.0.0.1")
    monkeypatch.setenv("SERVER_PORT", "8080")

    settings = ServerSettings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8080


def test_server_settings_supports_doorae_server(monkeypatch):
    """DOORAE_SERVER 환경변수 테스트."""
    monkeypatch.setenv("DOORAE_SERVER", "127.0.0.1:9100")

    settings = ServerSettings()

    assert settings.server == "127.0.0.1:9100"
    assert settings.host == "127.0.0.1"
    assert settings.port == 9100
    assert settings.server_address == "127.0.0.1:9100"


def test_get_server_settings_cached():
    """캐싱 테스트."""
    settings1 = get_server_settings()
    settings2 = get_server_settings()
    assert settings1 is settings2
