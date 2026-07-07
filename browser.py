"""Browser automation for Railgun checkin using Playwright."""

from datetime import datetime
from pathlib import Path

from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PlaywrightTimeout


class RailgunBrowser:
    """Context-managed Chromium browser for Railgun login and checkin."""

    def __init__(self, headless: bool = True, screenshot_dir: str | Path = "screenshots"):
        self.headless = headless
        self.screenshot_dir = Path(screenshot_dir)
        self._playwright: Playwright | None = None
        self._browser = None
        self._context = None
        self.page = None

    def __enter__(self):
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self._context = self._browser.new_context(viewport={"width": 1280, "height": 800})
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

    def _screenshot(self, name: str) -> Path:
        """Save a screenshot to *screenshot_dir* and return the saved path."""
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        path = self.screenshot_dir / f"{name.rsplit('.', 1)[0]}_{timestamp}.png"
        self.page.screenshot(path=str(path))
        return path

    def _has_text(self, texts: list[str]) -> bool:
        """Return True if any of *texts* appears in the page (case-insensitive)."""
        content = self.page.content().lower()
        return any(text.lower() in content for text in texts)

    def open_login_page(self, url: str = "https://railgun.info/console/checkin") -> None:
        """打开 railgun 页面；如果当前是首页，先点击 Login 进入登录页。"""
        self.page.goto(url, wait_until="networkidle")

        # Railgun 首页有 Register / Login 两个入口，需要先点击 Login。
        login_button = 'button:has-text("Login"), button:has-text("登录"), a:has-text("Login"), a:has-text("登录")'
        try:
            self.page.locator(login_button).first.click(timeout=5_000)
            self.page.wait_for_load_state("networkidle")
        except PlaywrightTimeout:
            # 已经在登录页或没有 Login 按钮，继续后续流程。
            pass

    def request_verification_code(self, email: str) -> None:
        """在登录页输入邮箱并点击发送验证码。"""
        email_input = 'input[type="email"], input[name="email"], input[placeholder*="邮箱"]'
        send_button = 'button:has-text("发送"), button:has-text("验证码"), button:has-text("Send")'

        try:
            self.page.locator(email_input).fill(email)
            self.page.locator(send_button).click()
        except PlaywrightTimeout:
            self._screenshot("02_send_code_timeout")
            raise RuntimeError("Request verification code timed out")

        self.page.wait_for_timeout(1000)
        if self._has_text(["失败", "错误", "error", "fail", "无效"]):
            self._screenshot("02_send_code_failed")
            raise RuntimeError("Failed to request verification code")

    def is_login_page(self) -> bool:
        """Return True if the current URL indicates we are still on a login page."""
        url = self.page.url.lower()
        return "login" in url or "signin" in url

    def submit_verification_code(self, code: str) -> None:
        """输入验证码并点击登录，然后校验是否真正登录成功。"""
        code_input = 'input[type="text"], input[name="code"], input[placeholder*="验证码"]'
        login_button = 'button:has-text("登录"), button:has-text("登入"), button:has-text("Login")'

        try:
            self.page.locator(code_input).fill(code)
            self.page.locator(login_button).click()
            self.page.wait_for_load_state("networkidle")
        except PlaywrightTimeout:
            self._screenshot("03_login_submit_timeout")
            raise RuntimeError("Login submit timed out")

        self.page.wait_for_timeout(1000)

        if self.is_login_page():
            self._screenshot("04_login_failed")
            raise RuntimeError("Login failed: still on login page")

    def ensure_checkin_page(self, url: str = "https://railgun.info/console/checkin") -> None:
        """确保当前页面是打卡页，如果不是则导航过去。"""
        if not self.page.url.startswith(url):
            self.page.goto(url, wait_until="networkidle")

    def click_checkin(self, timeout: int = 30_000) -> bool:
        """点击打卡按钮。返回是否成功。"""
        checkin_button = 'button:has-text("打卡"), button:has-text("Check In"), a:has-text("打卡")'

        try:
            self.page.locator(checkin_button).first.click(timeout=timeout)
            self.page.wait_for_load_state("networkidle")
        except PlaywrightTimeout:
            self._screenshot("checkin_button_not_found")
            raise RuntimeError("Checkin button not found or click timed out")

        success = self._has_text(["成功", "已打卡", "checked in", "success"])
        failure = self._has_text(["失败", "error", "fail"])
        result = success and not failure
        self._screenshot("05_checkin_result")
        return result

    def save_screenshot(self, name: str) -> Path:
        """Save a screenshot with the given *name* and return the saved path."""
        return self._screenshot(name)
