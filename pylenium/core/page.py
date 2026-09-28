"""Facade for Selenium WebDriver, providing a Playwright-like API."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.config.config import settings
from pylenium.core.locator import Locator


def _xpath_literal(text: str) -> str:
    """Escape text for use in XPath.

    If it contains no single quotes, wrap in single quotes.
    If it contains no double quotes, wrap in double quotes.
    If it contains both, construct a concat() expression.
    """
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    parts = text.split("'")
    return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"


class Page:
    """Simplified Playwright-like interface wrapping Selenium WebDriver."""

    def __init__(self, driver: WebDriver, *, base_url: str | None = None):
        self._driver = driver
        self._base_url = base_url

    def goto(self, url: str) -> None:
        """Navigate to the given URL.

        Resolve relative URLs with urllib.parse.urljoin. Absolute URLs,
        including file: and data:, are passed unchanged.
        """
        if not urlsplit(url).scheme:
            base_url = self._base_url
            if base_url is None:
                base_url = settings.get("browser.base_url", "")
            if base_url:
                url = urljoin(base_url.rstrip("/") + "/", url)
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
        - Starts with '/' or '(' -> XPath
        - Everything else -> CSS

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
        if name is not None:
            escaped_name = _xpath_literal(name)
            xpath = (
                f"//*[@role={_xpath_literal(role)}]"
                f"[normalize-space(@aria-label)={escaped_name} or "
                f"normalize-space(text())={escaped_name}]"
            )
        else:
            xpath = f"//*[@role={_xpath_literal(role)}]"
        return Locator(xpath, driver=self._driver)

    def get_by_text(self, text: str) -> Locator:
        """Create a Locator that finds elements containing the given text.

        Args:
            text: The text content to search for.

        Returns:
            A lazy Locator instance.
        """
        xpath = f"//*[normalize-space(text())={_xpath_literal(text)}]"
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
        """Close the current window; closing the last window ends the session."""
        self._driver.close()
