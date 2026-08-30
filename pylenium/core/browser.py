"""Browser lifecycle management.

Uses Dynaconf settings for configuration and delegates
driver creation to BrowserFactory + BrowserStrategy.
"""

from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.config.config import settings
from pylenium.core.browser_factory import BrowserFactory
from pylenium.core.browser_options import BrowserOptions
from pylenium.core.page import Page


class Browser:
    """Represents a browser session, managing the WebDriver instance."""

    def __init__(self, driver: WebDriver):
        self._driver = driver

    @classmethod
    def launch(cls, browser_type: str | None = None, headless: bool | None = None) -> Browser:
        """Launch a new browser instance based on config or provided arguments.

        Args:
            browser_type: Override the browser type from config.
            headless: Override the headless setting from config.

        Returns:
            A new Browser instance.
        """
        b_type = browser_type or settings.get("browser.type", "chrome")
        is_headless = headless if headless is not None else settings.get("browser.headless", False)

        options = BrowserOptions(b_type)
        if is_headless:
            options.headless(True)

        window_size = settings.get("browser.window_size", "1920x1080")
        if window_size:
            w, h = map(int, window_size.split("x"))
            options.window_size(w, h)

        driver = BrowserFactory.create(b_type, options)

        timeout = settings.get("browser.page_load_timeout", 30)
        if timeout:
            driver.set_page_load_timeout(timeout)

        return cls(driver)

    def new_page(self) -> Page:
        """Create a new Page object associated with this browser."""
        return Page(self._driver)

    def close(self) -> None:
        """Quit the browser session."""
        if self._driver:
            self._driver.quit()
