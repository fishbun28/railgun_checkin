"""Main orchestration for the Railgun auto-checkin flow."""

import os
import sys
import time
from datetime import datetime
from email.message import Message
from pathlib import Path

from browser import RailgunBrowser
from config import load_config
from logger import setup_logger
from mail_client import QQMailClient


LOCK_FILE = Path("checkin.lock")

CODE_REQUEST_DELAY = 5
MAIL_MAX_ATTEMPTS = 12
MAIL_POLL_INTERVAL = 5
LOCK_TIMEOUT_SECONDS = 300


def _read_lock_pid() -> str:
    """Read the PID stored in the lock file, if possible."""
    try:
        return LOCK_FILE.read_text(encoding="utf-8").splitlines()[0]
    except Exception:
        return "unknown"


def _read_lock_timestamp() -> datetime | None:
    """Read the timestamp stored in the lock file, if possible."""
    try:
        text = LOCK_FILE.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) >= 2:
            return datetime.fromisoformat(lines[1])
    except Exception:
        pass
    return None


def acquire_lock() -> bool:
    """Create the lock file atomically if it does not already exist.

    Returns:
        True if the lock was acquired, False if another instance is running.
    """
    try:
        with open(LOCK_FILE, "x", encoding="utf-8") as f:
            f.write(f"{os.getpid()}\n{datetime.now().isoformat()}\n{str(sys.argv)}")
        return True
    except FileExistsError:
        timestamp = _read_lock_timestamp()
        if timestamp is not None:
            age = (datetime.now() - timestamp).total_seconds()
            if age > LOCK_TIMEOUT_SECONDS:
                logger = setup_logger("railgun-checkin", _log_file_path())
                logger.warning(
                    "Stale lock file detected (age %d seconds); removing and retrying.",
                    int(age),
                )
                try:
                    LOCK_FILE.unlink()
                except OSError:
                    pass
                return acquire_lock()
        pid = _read_lock_pid()
        print(f"Another instance is running (PID {pid}). Exiting.")
        return False
    except Exception as e:
        logger = setup_logger("railgun-checkin", _log_file_path())
        logger.error(f"Failed to acquire lock: {e}")
        return False


def _log_file_path() -> Path:
    """Return the log file path based on the current date."""
    return Path("logs") / f"checkin-{datetime.now():%Y-%m-%d}.log"


def release_lock() -> None:
    """Remove the lock file if it exists."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def run() -> int:
    """Run the full checkin flow.

    Returns:
        0 on success, 1 on failure.
    """
    LOG_FILE = _log_file_path()

    def _subject_predicate(msg: Message) -> bool:
        """Return True if the email subject mentions railgun or verification code."""
        subject = (msg.get("Subject") or "").lower()
        return "railgun" in subject or "验证码" in subject

    logger = setup_logger("railgun-checkin", LOG_FILE)

    if not acquire_lock():
        logger.warning("Another checkin instance is already running.")
        return 1

    browser = None
    try:
        cfg = load_config()
        logger.info("Configuration loaded.")

        with RailgunBrowser() as browser:
            try:
                logger.info("Opening login page...")
                browser.open_login_page()
                browser.save_screenshot("01_login_page")

                logger.info("Requesting verification code...")
                browser.request_verification_code(cfg.railgun_email)
                time.sleep(CODE_REQUEST_DELAY)

                logger.info("Reading verification code from QQ mail...")
                client = QQMailClient(
                    cfg.qq_email,
                    cfg.qq_auth_code,
                    cfg.imap_server,
                    cfg.imap_port,
                )
                code = client.find_code(
                    predicate=_subject_predicate,
                    max_attempts=MAIL_MAX_ATTEMPTS,
                    interval=MAIL_POLL_INTERVAL,
                )
                if not code:
                    logger.error("Failed to find verification code in QQ Mail.")
                    browser.save_screenshot("02_no_code")
                    return 1

                logger.info("Verification code retrieved.")
                logger.info("Submitting verification code...")
                browser.submit_verification_code(code)
                browser.save_screenshot("03_after_login")

                logger.info("Navigating to checkin page...")
                browser.ensure_checkin_page()
                browser.save_screenshot("04_checkin_page")

                logger.info("Clicking checkin button...")
                if not browser.click_checkin():
                    logger.error("Checkin failed after clicking the button.")
                    browser.save_screenshot("05_checkin_failed")
                    return 1

                logger.info("Checkin succeeded.")
                browser.save_screenshot("05_checkin_success")
                return 0

            except RuntimeError as exc:
                logger.error("Browser operation failed: %s", exc)
                try:
                    browser.save_screenshot("error")
                except Exception:
                    pass
                return 1

    except Exception as exc:
        logger.exception("Unexpected error during checkin: %s", exc)
        if browser is not None:
            try:
                browser.save_screenshot("error")
            except Exception:
                pass
        return 1

    finally:
        release_lock()


if __name__ == "__main__":
    sys.exit(run())
