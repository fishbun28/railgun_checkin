import os
import pytest
from config import load_config, Config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("RAILGUN_EMAIL", "user@example.com")
    monkeypatch.setenv("QQ_EMAIL", "qq@qq.com")
    monkeypatch.setenv("QQ_AUTH_CODE", "auth123")
    monkeypatch.setenv("RUN_TIME", "10:00")

    cfg = load_config()
    assert cfg.railgun_email == "user@example.com"
    assert cfg.qq_email == "qq@qq.com"
    assert cfg.qq_auth_code == "auth123"
    assert cfg.run_time == "10:00"


def test_load_config_missing_raises(monkeypatch):
    monkeypatch.delenv("RAILGUN_EMAIL", raising=False)
    monkeypatch.delenv("QQ_EMAIL", raising=False)
    monkeypatch.delenv("QQ_AUTH_CODE", raising=False)
    with pytest.raises(ValueError):
        load_config()
