"""Facade for Selenium WebDriver, providing a Playwright-like API."""

from __future__ import annotations

from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.config.config import settings
from pylenium.core.locator import Locator


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

    # -- Locator creation methods --

    def locator(self, selector: str) -> Locator:
        """Create a Locator for the given CSS or XPath selector.

        Selector type is auto-detected:
        - Starts with '/' or '(' → XPath
        - Everything else → CSS

        Args:
            selector: A CSS or XPath selector string.

        Returns:
            A lazy Locator instance.
        """
        return Locator(selector, driver=self._driver)

    def get_by_role(self, role: str, name: str | None = None) -> Locator:
        """Create a Locator that finds elements by their ARIA role.

        Uses a simplified XPath matching on the 'role' attribute
        and optionally filters by accessible name (aria-label or text content).

        Args:
            role: The ARIA role to search for (e.g., 'button', 'link').
            name: Optional accessible name to filter by.

        Returns:
            A lazy Locator instance.
        """
        if name:
            xpath = (
                f"//*[@role='{role}']"
                f"[normalize-space(@aria-label)='{name}' or "
                f"normalize-space(text())='{name}']"
            )
        else:
            xpath = f"//*[@role='{role}']"
        return Locator(xpath, driver=self._driver)

    def get_by_text(self, text: str) -> Locator:
        """Create a Locator that finds elements containing the given text.

        Args:
            text: The text content to search for.

        Returns:
            A lazy Locator instance.
        """
        xpath = f"//*[normalize-space(text())='{text}']"
        return Locator(xpath, driver=self._driver)

    # -- Page actions --

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
