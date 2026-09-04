"""Facade for Selenium WebDriver, providing a Playwright-like API."""

from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.config.config import settings


class Page:
    """Simplified Playwright-like interface wrapping Selenium WebDriver."""

    def __init__(self, driver: WebDriver):
        self._driver = driver

    def goto(self, url: str) -> None:
        """Navigate to the given URL.

        If the URL does not start with 'http', it will be prepended
        with the base_url from configuration.
        """
        if not url.startswith("http"):
            base_url = settings.get("browser.base_url", "")
            if base_url:
                url = base_url.rstrip("/") + "/" + url.lstrip("/")
        self._driver.get(url)

    def title(self) -> str:
        """Get the page title."""
        return self._driver.title

    def url(self) -> str:
        """Get the current URL."""
        return self._driver.current_url

    def screenshot(self, path: str) -> bytes:
        """Take a screenshot and save it to the specified path.

        Returns:
            The screenshot data as bytes.
        """
        self._driver.save_screenshot(path)
        return self._driver.get_screenshot_as_png()

    def close(self) -> None:
        """Close the page and its underlying driver."""
        self._driver.close()

    # Note: Locator methods (locator, get_by_role, etc.) will be added in Phase 3
