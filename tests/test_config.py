import pytest
from config import load_config


def test_load_config_reads_env(monkeypatch):
    monkeypatch.setenv("RAILGUN_EMAIL", "user@example.com")
    monkeypatch.setenv("QQ_EMAIL", "qq@qq.com")
    monkeypatch.setenv("QQ_AUTH_CODE", "auth123")
    monkeypatch.setenv("RUN_TIME", "10:00")
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)

    cfg = load_config()
    assert cfg.railgun_email == "user@example.com"
    assert cfg.qq_email == "qq@qq.com"
    assert cfg.qq_auth_code == "auth123"
    assert cfg.run_time == "10:00"


def test_load_config_custom_imap_port(monkeypatch):
    monkeypatch.setenv("RAILGUN_EMAIL", "user@example.com")
    monkeypatch.setenv("QQ_EMAIL", "qq@qq.com")
    monkeypatch.setenv("QQ_AUTH_CODE", "auth123")
    monkeypatch.setenv("IMAP_PORT", "995")
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    cfg = load_config()
    assert cfg.imap_port == 995


def test_load_config_defaults(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("RUN_TIME", raising=False)
    monkeypatch.delenv("IMAP_SERVER", raising=False)
    monkeypatch.delenv("IMAP_PORT", raising=False)
    monkeypatch.setenv("RAILGUN_EMAIL", "user@example.com")
    monkeypatch.setenv("QQ_EMAIL", "qq@qq.com")
    monkeypatch.setenv("QQ_AUTH_CODE", "auth123")

    cfg = load_config()
    assert cfg.imap_server == "imap.qq.com"
    assert cfg.imap_port == 993
    assert cfg.run_time == "09:00"


def test_load_config_missing_raises(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.delenv("RAILGUN_EMAIL", raising=False)
    monkeypatch.delenv("QQ_EMAIL", raising=False)
    monkeypatch.delenv("QQ_AUTH_CODE", raising=False)
    with pytest.raises(ValueError, match="Missing required environment variables") as exc_info:
        load_config()
    message = str(exc_info.value)
    assert "RAILGUN_EMAIL" in message
    assert "QQ_EMAIL" in message
    assert "QQ_AUTH_CODE" in message


def test_load_config_invalid_imap_port(monkeypatch):
    monkeypatch.setattr("config.load_dotenv", lambda *a, **k: None)
    monkeypatch.setenv("RAILGUN_EMAIL", "user@example.com")
    monkeypatch.setenv("QQ_EMAIL", "qq@qq.com")
    monkeypatch.setenv("QQ_AUTH_CODE", "auth123")
    monkeypatch.setenv("IMAP_PORT", "not-a-number")

    with pytest.raises(ValueError, match="IMAP_PORT must be an integer, got: 'not-a-number'"):
        load_config()


def test_load_config_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("RAILGUN_EMAIL", raising=False)
    monkeypatch.delenv("QQ_EMAIL", raising=False)
    monkeypatch.delenv("QQ_AUTH_CODE", raising=False)

    env_file = tmp_path / ".env"
    env_file.write_text(
        "RAILGUN_EMAIL=file@example.com\n"
        "QQ_EMAIL=qqfile@qq.com\n"
        "QQ_AUTH_CODE=fileauth123\n"
    )

    cfg = load_config(env_path=str(env_file))
    assert cfg.railgun_email == "file@example.com"
    assert cfg.qq_email == "qqfile@qq.com"
    assert cfg.qq_auth_code == "fileauth123"
