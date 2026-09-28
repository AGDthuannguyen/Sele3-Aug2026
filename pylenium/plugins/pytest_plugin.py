"""Function-scoped browser sessions and CLI overrides for pytest."""

from collections.abc import Iterator

import pytest

from pylenium.core.browser import Browser
from pylenium.core.page import Page


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pylenium")
    group.addoption("--browser", choices=("chrome", "firefox", "edge", "safari"), default=None,
                    help="Override the configured browser")
    group.addoption("--headless", action="store_true", default=False,
                    help="Run without a visible browser window")
    group.addoption("--headed", action="store_true", default=False,
                    help="Run with a visible browser window")
    group.addoption("--base-url", default=None, help="Base URL for relative page navigation")


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--headless") and config.getoption("--headed"):
        raise pytest.UsageError("Choose either --headless or --headed")


@pytest.fixture
def browser(pytestconfig: pytest.Config) -> Iterator[Browser]:
    """Own one session per test and close it even when dependent setup fails."""
    headless = None
    if pytestconfig.getoption("--headless"):
        headless = True
    elif pytestconfig.getoption("--headed"):
        headless = False
    session = Browser.launch(browser_type=pytestconfig.getoption("--browser"), headless=headless)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def page(browser: Browser, pytestconfig: pytest.Config) -> Page:
    """Wrap the session's current window; browser owns session cleanup."""
    return browser.new_page(base_url=pytestconfig.getoption("--base-url"))
