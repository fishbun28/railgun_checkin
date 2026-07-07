"""Main orchestration for the Railgun auto-checkin flow."""

import sys
import time
from datetime import datetime
from pathlib import Path

from browser import RailgunBrowser
from config import load_config
from logger import setup_logger
from mail_client import QQMailClient


LOCK_FILE = Path("checkin.lock")
LOG_FILE = Path("logs") / f"checkin-{datetime.now().strftime('%Y-%m-%d')}.log"


def acquire_lock() -> bool:
    """Create the lock file if it does not already exist.

    Returns:
        True if the lock was acquired, False if another instance is running.
    """
    if LOCK_FILE.exists():
        return False
    LOCK_FILE.write_text(str(datetime.now().isoformat()), encoding="utf-8")
    return True


def release_lock() -> None:
    """Remove the lock file if it exists."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except OSError:
        pass


def _subject_predicate(msg) -> bool:
    """Return True if the email subject mentions railgun or verification code."""
    subject = (msg.get("Subject") or "").lower()
    return "railgun" in subject or "验证码" in subject


def run() -> int:
    """Run the full checkin flow.

    Returns:
        0 on success, 1 on failure.
    """
    logger = setup_logger("railgun-checkin", LOG_FILE)

    if not acquire_lock():
        logger.warning("Another checkin instance is already running.")
        return 1

    browser = None
    try:
        cfg = load_config()

        with RailgunBrowser() as browser:
            try:
                browser.open_login_page()
                browser.save_screenshot("01_login_page")

                browser.request_verification_code(cfg.railgun_email)
                time.sleep(5)

                client = QQMailClient(
                    cfg.qq_email,
                    cfg.qq_auth_code,
                    cfg.imap_server,
                    cfg.imap_port,
                )
                code = client.find_code(predicate=_subject_predicate)
                if not code:
                    logger.error("Failed to find verification code in QQ Mail.")
                    browser.save_screenshot("02_no_code")
                    return 1

                browser.submit_verification_code(code)

                browser.ensure_checkin_page()
                browser.save_screenshot("04_checkin_page")

                if not browser.click_checkin():
                    logger.error("Checkin failed after clicking the button.")
                    browser.save_screenshot("05_checkin_failed")
                    return 1

                logger.info("Checkin completed successfully.")
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
