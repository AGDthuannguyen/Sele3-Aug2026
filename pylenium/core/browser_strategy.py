"""Browser strategy classes to encapsulate browser-specific logic.

Each strategy handles both options creation and driver initialization
for a specific browser type, eliminating duplicated if-else blocks
across BrowserFactory and BrowserOptions.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.remote.webdriver import WebDriver


class BrowserStrategy(ABC):
    """Abstract base class for browser-specific strategies."""

    @abstractmethod
    def create_options(self) -> Any:
        """Create and return a browser-specific options object."""

    @abstractmethod
    def create_driver(self, options: Any) -> WebDriver:
        """Create and return a WebDriver instance with the given options."""

    @abstractmethod
    def apply_headless(self, options: Any) -> None:
        """Apply headless mode to the given options object."""


class ChromeStrategy(BrowserStrategy):
    """Strategy for Google Chrome browser."""

    def create_options(self) -> ChromeOptions:
        return ChromeOptions()

    def create_driver(self, options: Any) -> WebDriver:
        return webdriver.Chrome(options=options)

    def apply_headless(self, options: Any) -> None:
        options.add_argument("--headless=new")


class FirefoxStrategy(BrowserStrategy):
    """Strategy for Mozilla Firefox browser."""

    def create_options(self) -> FirefoxOptions:
        return FirefoxOptions()

    def create_driver(self, options: Any) -> WebDriver:
        return webdriver.Firefox(options=options)

    def apply_headless(self, options: Any) -> None:
        options.add_argument("-headless")


class EdgeStrategy(BrowserStrategy):
    """Strategy for Microsoft Edge browser."""

    def create_options(self) -> EdgeOptions:
        return EdgeOptions()

    def create_driver(self, options: Any) -> WebDriver:
        return webdriver.Edge(options=options)

    def apply_headless(self, options: Any) -> None:
        options.add_argument("--headless=new")


class SafariStrategy(BrowserStrategy):
    """Strategy for Apple Safari browser."""

    def create_options(self) -> None:
        # Safari does not use standard options
        return None

    def create_driver(self, options: Any) -> WebDriver:
        return webdriver.Safari()

    def apply_headless(self, options: Any) -> None:
        # Safari does not support headless mode
        pass


# Registry mapping browser type names to their strategy classes
BROWSER_STRATEGIES: dict[str, type[BrowserStrategy]] = {
    "chrome": ChromeStrategy,
    "firefox": FirefoxStrategy,
    "edge": EdgeStrategy,
    "safari": SafariStrategy,
}


def get_strategy(browser_type: str) -> BrowserStrategy:
    """Get the strategy instance for the given browser type.

    Args:
        browser_type: The name of the browser (e.g., 'chrome', 'firefox').

    Returns:
        A BrowserStrategy instance for the specified browser type.

    Raises:
        ValueError: If the browser type is not supported.
    """
    browser_type = browser_type.lower()
    strategy_cls = BROWSER_STRATEGIES.get(browser_type)
    if strategy_cls is None:
        supported = ", ".join(BROWSER_STRATEGIES.keys())
        raise ValueError(
            f"Unsupported browser type: '{browser_type}'. "
            f"Supported browsers: {supported}"
        )
    return strategy_cls()
