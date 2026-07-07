"""Browser automation for Railgun checkin using Playwright."""

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
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._context = None
        self.page = None

    def _screenshot(self, name: str) -> Path:
        """Save a screenshot to *screenshot_dir* and return the saved path."""
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        path = self.screenshot_dir / name
        self.page.screenshot(path=str(path))
        return path

    def open_login_page(self, url: str = "https://railgun.info/console/checkin") -> None:
        """打开 railgun 页面；未登录时会自动重定向到登录页。"""
        self.page.goto(url, wait_until="networkidle")

    def request_verification_code(self, email: str) -> None:
        """在登录页输入邮箱并点击发送验证码。"""
        email_input = 'input[type="email"], input[name="email"], input[placeholder*="邮箱"]'
        send_button = 'button:has-text("发送"), button:has-text("验证码"), button:has-text("Send")'

        self.page.locator(email_input).fill(email)
        self.page.locator(send_button).click()

    def submit_verification_code(self, code: str) -> None:
        """输入验证码并点击登录。"""
        code_input = 'input[type="text"], input[name="code"], input[placeholder*="验证码"]'
        login_button = 'button:has-text("登录"), button:has-text("登入"), button:has-text("Login")'

        self.page.locator(code_input).fill(code)
        self.page.locator(login_button).click()
        self.page.wait_for_load_state("networkidle")

    def ensure_checkin_page(self, url: str = "https://railgun.info/console/checkin") -> None:
        """确保当前页面是打卡页，如果不是则导航过去。"""
        if self.page.url != url:
            self.page.goto(url, wait_until="networkidle")

    def click_checkin(self, timeout: int = 30_000) -> bool:
        """点击打卡按钮。返回是否成功。"""
        checkin_button = 'button:has-text("打卡"), button:has-text("Check In"), a:has-text("打卡")'

        try:
            self.page.locator(checkin_button).first.click(timeout=timeout)
            self.page.wait_for_load_state("networkidle")
            return True
        except PlaywrightTimeout:
            self._screenshot("checkin_button_not_found.png")
            return False

    def save_screenshot(self, name: str) -> Path:
        """Save a screenshot with the given *name* and return the saved path."""
        return self._screenshot(name)
