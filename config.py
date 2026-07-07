"""Configuration module for railgun auto-checkin."""

from dataclasses import dataclass
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    railgun_email: str
    qq_email: str
    qq_auth_code: str
    run_time: str = "09:00"
    imap_server: str = "imap.qq.com"
    imap_port: int = 993


def load_config(env_path: str | None = None) -> Config:
    """Load configuration from environment variables.

    Args:
        env_path: Optional path to a .env file. If provided, variables from that
            file are loaded into the environment. If omitted, the default `.env`
            file in the current working directory is loaded.

    Returns:
        A populated Config instance.

    Raises:
        ValueError: If any required environment variable is missing.
    """
    if env_path is not None:
        load_dotenv(Path(env_path), override=True)
    else:
        load_dotenv()

    required_vars = ["RAILGUN_EMAIL", "QQ_EMAIL", "QQ_AUTH_CODE"]
    missing = [var for var in required_vars if not getenv(var)]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        railgun_email=getenv("RAILGUN_EMAIL", ""),
        qq_email=getenv("QQ_EMAIL", ""),
        qq_auth_code=getenv("QQ_AUTH_CODE", ""),
        run_time=getenv("RUN_TIME", "09:00"),
        imap_server=getenv("IMAP_SERVER", "imap.qq.com"),
        imap_port=int(getenv("IMAP_PORT", "993")),
    )
