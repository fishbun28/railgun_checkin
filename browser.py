"""Browser automation for Railgun checkin using Playwright.

The Railgun console is a SPA whose button labels have changed more than once
("Login" / "Sign in" / "登录").  Every locator here therefore lists several
acceptable variants and falls back to structural selectors (``type=submit``,
input ids/names) so a wording change alone cannot break the daily run.
"""

from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import Locator, Playwright, TimeoutError as PlaywrightTimeout, sync_playwright


DEFAULT_CONSOLE_URL = "https://railgun.info/console/checkin"

# --- selectors -------------------------------------------------------------

EMAIL_INPUT = ', '.join(
    [
        'input#email',
        'input[name="email"]',
        'input[type="email"]',
    ]
)

CODE_INPUT = ', '.join(
    [
        'input#mailcode',
        'input[name="mailcode"]',
        'input[name="code"]',
        'input[placeholder*="验证码"]',
        'input[placeholder*="code"]',
    ]
)

SEND_CODE_BUTTON = ', '.join(
    [
        'button:has-text("Send code")',
        'button:has-text("Get code")',
        'button:has-text("Send verification")',
        'button:has-text("发送验证码")',
        'button:has-text("获取验证码")',
        'button:has-text("发送")',
    ]
)

SUBMIT_BUTTON = ', '.join(
    [
        'button[type="submit"]',
        'button:has-text("Sign in")',
        'button:has-text("Sign-in")',
        'button:has-text("Login")',
        'button:has-text("登录")',
        'button:has-text("登入")',
    ]
)

LOGIN_ENTRY = ', '.join(
    [
        'a[href="/login"]',
        'a[href="/signin"]',
        'a[href="/sign-in"]',
        'a:has-text("Login")',
        'a:has-text("Sign in")',
        'button:has-text("Login")',
        'button:has-text("Sign in")',
    ]
)

# 打卡控件按优先级分组：先真正的打卡按钮，最后才是站点内部的导航链接
# （例如积分页右上角的「去首页签到」），避免点错元素。
CHECKIN_BUTTON_GROUPS = [
    [
        'button:has-text("立即签到")',
        'button:has-text("立即打卡")',
        'button:has-text("打卡")',
        'button:has-text("签到")',
        'button:has-text("Check in")',
        'button:has-text("Check-in")',
    ],
    [
        'a:has-text("去首页签到")',
        'a:has-text("去签到")',
        'a:has-text("每日签到")',
    ],
]

# --- page-state keywords ---------------------------------------------------

SEND_CODE_ERRORS = [
    "发送失败",
    "请求过于频繁",
    "操作频繁",
    "too many requests",
    "rate limit",
    "invalid email",
    "邮箱格式",
]

CHECKIN_SUCCESS = [
    "打卡成功",
    "签到成功",
    "已打卡",
    "already checked",
    "already checked in",
    "checked in",
    "check-in success",
    "check-in successful",
]

CHECKIN_FAILURE = [
    "打卡失败",
    "签到失败",
    "failed",
    "失败",
]

# 已经签到过时页面上的提示；命中即视为成功，避免把「今天已签到」误报成失败。
ALREADY_CHECKEDIN = [
    "今日已签到",
    "今日已打卡",
    "今天已打卡",
    "已签到",
    "已打卡",
    "already checked in",
    "already checked",
]


class RailgunBrowser:
    """Context-managed Chromium browser for Railgun login and checkin."""

    def __init__(
        self,
        headless: bool = True,
        screenshot_dir: str | Path = "screenshots",
        slow_mo: int = 0,
    ):
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self.slow_mo = slow_mo
        self._playwright: Playwright | None = None
        self._browser = None
        self._context = None
        self.page = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(
            headless=self.headless, slow_mo=self.slow_mo
        )
        self._context = self._browser.new_context(viewport={"width": 1280, "height": 800})
        self._context.set_default_timeout(30_000)
        self.page = self._context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self.page = None

    # --- helpers ----------------------------------------------------------

    def _screenshot(self, name: str) -> Path:
        """Save a screenshot to *screenshot_dir* and return the saved path."""
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.screenshot_dir / f"{name.rsplit('.', 1)[0]}_{timestamp}.png"
        try:
            self.page.screenshot(path=str(path))
        except Exception:
            pass
        return path

    def _first_visible(self, selector: str) -> Locator | None:
        """Return the first visible element matching *selector*, else None."""
        try:
            locator = self.page.locator(selector)
            count = locator.count()
        except Exception:
            return None
        for index in range(count):
            candidate = locator.nth(index)
            try:
                if candidate.is_visible():
                    return candidate
            except Exception:
                continue
        return None

    def _first_visible_any(self, groups: list[list[str]]) -> Locator | None:
        """Return the first visible element, trying selector groups in priority order."""
        for group in groups:
            found = self._first_visible(", ".join(group))
            if found is not None:
                return found
        return None

    def _wait_visible(self, selector: str, timeout_ms: int) -> Locator | None:
        """Poll until a visible element matching *selector* appears."""
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            found = self._first_visible(selector)
            if found is not None:
                return found
            self.page.wait_for_timeout(250)
        return None

    def _body_text(self) -> str:
        """Lower-cased text of the rendered page body (falls back to HTML)."""
        try:
            return (self.page.inner_text("body") or "").lower()
        except Exception:
            try:
                return self.page.content().lower()
            except Exception:
                return ""

    def _has_text(self, texts: list[str]) -> bool:
        """Return True if any of *texts* appears in the rendered page text."""
        content = self._body_text()
        return any(text.lower() in content for text in texts)

    def _login_form_visible(self) -> bool:
        """Return True while the verification-code login form is on screen."""
        return self._first_visible(CODE_INPUT) is not None

    # --- flow steps -------------------------------------------------------

    def open_login_page(self, url: str = DEFAULT_CONSOLE_URL, timeout_ms: int = 30_000) -> None:
        """打开 railgun 页面；未登录时会跳首页，需要点击 Login 进入登录页。"""
        self.page.goto(url, wait_until="networkidle", timeout=60_000)

        if self._login_form_visible():
            return

        entry = self._first_visible(LOGIN_ENTRY)
        if entry is not None:
            try:
                entry.click(timeout=10_000)
            except PlaywrightTimeout:
                pass

        if self._wait_visible(CODE_INPUT, timeout_ms) is not None:
            return

        self._screenshot("01_login_page_not_found")
        raise RuntimeError(f"Could not reach the login form (url={self.page.url})")

    def request_verification_code(self, email: str) -> None:
        """在登录页输入邮箱并点击发送验证码。"""
        email_input = self._wait_visible(EMAIL_INPUT, 15_000)
        if email_input is None:
            self._screenshot("02_email_input_not_found")
            raise RuntimeError("Email input not found on the login page")

        try:
            email_input.fill(email, timeout=10_000)
        except PlaywrightTimeout:
            self._screenshot("02_email_fill_timeout")
            raise RuntimeError("Filling the email address timed out")

        send_button = self._wait_visible(SEND_CODE_BUTTON, 10_000)
        if send_button is None:
            self._screenshot("02_send_code_timeout")
            raise RuntimeError("Send-code button not found on the login page")

        try:
            send_button.click(timeout=10_000)
        except PlaywrightTimeout:
            self._screenshot("02_send_code_timeout")
            raise RuntimeError("Clicking the send-code button timed out")

        self.page.wait_for_timeout(1500)
        if self._has_text(SEND_CODE_ERRORS):
            self._screenshot("02_send_code_failed")
            raise RuntimeError("Failed to request verification code")

    def is_login_page(self) -> bool:
        """Return True if we are still on the login / verification-code page."""
        url = self.page.url.lower()
        if any(hint in url for hint in ("/login", "/signin", "/sign-in")):
            return True
        return self._login_form_visible()

    def submit_verification_code(self, code: str, timeout_ms: int = 90_000) -> None:
        """输入验证码并点击登录，然后轮询确认是否真正离开登录页。

        旧实现直接 ``wait_for_load_state("networkidle")``：SPA 登录不一定会触发
        新的 load 事件，而且按钮文案一旦变化（Login -> Sign in）就会一直等到超时。
        这里改为轮询表单是否消失，并提供多种按钮文案 + ``type=submit`` 兜底。
        """
        code_input = self._wait_visible(CODE_INPUT, 10_000)
        if code_input is None:
            self._screenshot("03_code_input_not_found")
            raise RuntimeError("Verification-code input not found")

        try:
            code_input.fill(code, timeout=10_000)
        except PlaywrightTimeout:
            self._screenshot("03_code_fill_timeout")
            raise RuntimeError("Filling the verification code timed out")

        submit_button = self._wait_visible(SUBMIT_BUTTON, 10_000)
        if submit_button is None:
            self._screenshot("03_login_submit_timeout")
            raise RuntimeError("Login button not found (no matching Login/Sign in/submit button)")

        try:
            submit_button.click(timeout=10_000)
        except PlaywrightTimeout:
            self._screenshot("03_login_submit_timeout")
            raise RuntimeError("Clicking the login button timed out")

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if not self._login_form_visible():
                break
            self.page.wait_for_timeout(500)
        else:
            self._screenshot("03_login_submit_timeout")
            raise RuntimeError(
                f"Login did not complete after {timeout_ms // 1000}s "
                f"(url={self.page.url})"
            )

        # 表单消失后再给页面一次路由/渲染稳定的机会，失败也不影响结果。
        try:
            self.page.wait_for_load_state("domcontentloaded", timeout=10_000)
        except PlaywrightTimeout:
            pass

        if self.is_login_page():
            self._screenshot("04_login_failed")
            raise RuntimeError(f"Login failed: still on the login page (url={self.page.url})")

    def ensure_checkin_page(self, url: str = DEFAULT_CONSOLE_URL, timeout_ms: int = 30_000) -> None:
        """确保当前页面是打卡页，如果不是则导航过去。

        该页面带有实时流量图表，长时间轮询请求会让 ``networkidle`` 拖到几十秒，
        所以这里只等 DOM 就绪，后续由 click_checkin 轮询真正的签到控件。
        """
        if not self.page.url.startswith(url):
            self.page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        # 会话未生效时会被弹回登录页，此时要明确报错而不是让后续步骤空转。
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if self._login_form_visible():
                self._screenshot("04_login_required")
                raise RuntimeError(f"Login required: redirected back to the login page (url={self.page.url})")
            if self.page.url.startswith(url):
                break
            self.page.wait_for_timeout(250)

    def click_checkin(self, timeout: int = 60_000) -> bool:
        """点击打卡按钮。已经签到过时直接返回 True（幂等）。"""
        deadline = time.monotonic() + timeout / 1000

        while time.monotonic() < deadline:
            # 已经签到过：视为成功，避免把「今日已签到」误报为失败。
            if self._has_text(ALREADY_CHECKEDIN):
                self._screenshot("05_checkin_already_done")
                return True

            button = self._first_visible(", ".join(CHECKIN_BUTTON_GROUPS[0]))
            if button is not None:
                try:
                    button.click(timeout=15_000)
                except PlaywrightTimeout:
                    self._screenshot("checkin_click_timeout")
                    raise RuntimeError("Clicking the checkin button timed out")
                self.page.wait_for_timeout(3000)
                break

            # 部分页面只提供「去首页签到」这类导航入口，点进去后重新找按钮。
            nav = self._first_visible(", ".join(CHECKIN_BUTTON_GROUPS[1]))
            if nav is not None:
                try:
                    nav.click(timeout=15_000)
                except PlaywrightTimeout:
                    pass
                self.page.wait_for_timeout(2000)
                continue

            self.page.wait_for_timeout(250)
        else:
            self._screenshot("checkin_button_not_found")
            raise RuntimeError(f"Checkin button not found within {timeout // 1000}s (url={self.page.url})")

        success = self._has_text(CHECKIN_SUCCESS) or self._has_text(ALREADY_CHECKEDIN)
        failure = self._has_text(CHECKIN_FAILURE)
        result = success and not failure
        self._screenshot("05_checkin_result")
        return result

    def save_screenshot(self, name: str) -> Path:
        """Save a screenshot with the given *name* and return the saved path."""
        return self._screenshot(name)
