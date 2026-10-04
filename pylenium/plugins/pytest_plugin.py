"""Per-test browser sessions, CLI overrides, and failure screenshots."""

import logging
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4

import pytest

from pylenium.config.config import settings
from pylenium.core.browser import Browser
from pylenium.core.page import Page


_browser_session = pytest.StashKey[Browser]()
logger = logging.getLogger(__name__)


@contextmanager
def _reporting_request_timeout(session: Browser) -> Iterator[None]:
    """Bound driver HTTP reads during diagnostics/cleanup, then restore settings.

    Selenium's page-load timeout does not bound screenshot or quit requests.
    HTTP retries can cause multiple reads; the CI step also has an outer limit.
    """
    config = session._driver.command_executor.client_config
    previous_timeout = config.timeout
    config.timeout = 10
    try:
        yield
    finally:
        config.timeout = previous_timeout


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("pylenium")
    group.addoption("--browser", choices=("chrome", "firefox", "edge", "safari"), default=None,
                    help="Override the configured browser")
    group.addoption("--headless", action="store_true", default=False,
                    help="Run without a visible browser window")
    group.addoption("--headed", action="store_true", default=False,
                    help="Run with a visible browser window")
    group.addoption("--base-url", default=None, help="Base URL for relative page navigation")
    group.addoption("--screenshots-dir", default="artifacts/screenshots",
                    help="Directory for failure screenshots")


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--headless") and config.getoption("--headed"):
        raise pytest.UsageError("Choose either --headless or --headed")


@pytest.fixture
def browser(pytestconfig: pytest.Config, request: pytest.FixtureRequest) -> Iterator[Browser]:
    """Own one session per test and close it even when dependent setup fails."""
    headless = None
    if pytestconfig.getoption("--headless"):
        headless = True
    elif pytestconfig.getoption("--headed"):
        headless = False
    session = Browser.launch(browser_type=pytestconfig.getoption("--browser"), headless=headless)
    request.node.stash[_browser_session] = session
    try:
        yield session
    finally:
        del request.node.stash[_browser_session]
        with _reporting_request_timeout(session):
            session.close()


@pytest.fixture
def page(browser: Browser, pytestconfig: pytest.Config) -> Page:
    """Wrap the session's current window; browser owns session cleanup."""
    return browser.new_page(base_url=pytestconfig.getoption("--base-url"))


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_makereport(
    item: pytest.Item, call: pytest.CallInfo,
) -> Generator[None, pytest.TestReport, pytest.TestReport]:
    """Capture setup/call failures while the fixture's session is still alive."""
    report = yield
    session = item.stash.get(_browser_session, None)
    if not report.failed or report.when not in ("setup", "call") or session is None:
        return report
    if not settings.get("reporting.screenshot_on_failure", True):
        return report

    # Reporting is best-effort: its errors must not mask the original failure.
    try:
        directory = Path(item.config.getoption("--screenshots-dir"))
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{report.when}-{uuid4().hex}.png"
        with _reporting_request_timeout(session):
            image = Page(session._driver).screenshot(str(path))
        report.sections.append(("Failure screenshot", str(path)))
        if item.config.pluginmanager.hasplugin("allure_pytest"):
            import allure

            allure.attach(image, name=f"{item.nodeid} ({report.when})",
                          attachment_type=allure.attachment_type.PNG)
    except Exception as error:
        diagnostic = f"Failure screenshot unavailable: {type(error).__name__}: {error}"
        report.sections.append(("Screenshot capture error", diagnostic))
        logger.warning(diagnostic)
    return report
