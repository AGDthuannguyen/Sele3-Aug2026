"""Per-test browser sessions, CLI overrides, and failure screenshots."""

import json
import logging
import math
import shutil
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pytest

from pylenium.config.config import settings
from pylenium.core.browser import Browser
from pylenium.core.page import Page
from pylenium.reporting import StepRecorder, current_recorder, install_recorder, reset_recorder


_browser_session = pytest.StashKey[Browser]()
_previous_timeout_settings = pytest.StashKey[dict[str, object]]()
_run_directory = pytest.StashKey[Path]()
logger = logging.getLogger(__name__)

_TIMEOUT_OPTIONS = {
    "--page-load-timeout": "browser.page_load_timeout",
    "--action-timeout": "waits.timeout",
    "--assertion-timeout": "assertions.timeout",
}


def _latest_run_directory(root: Path) -> Path:
    """Start with an empty, predictable directory for this pytest invocation."""
    root.mkdir(parents=True, exist_ok=True)
    directory = root / "latest"
    if directory.is_symlink():
        raise pytest.UsageError(f"Report directory must not be a symlink: {directory}")
    if directory.exists():
        if not directory.is_dir():
            raise pytest.UsageError(f"Report path is not a directory: {directory}")
        shutil.rmtree(directory)
    directory.mkdir()
    return directory


def _configure_reports(config: pytest.Config) -> None:
    """Give one pytest invocation a report folder before reporter plugins initialize."""
    if hasattr(config, "workerinput"):
        directory = Path(config.workerinput["pylenium_run_directory"])
    else:
        root = Path(config.getoption("--reports-root"))
        directory = _latest_run_directory(root)
        (directory / "run.json").write_text(json.dumps({
            "started": datetime.now().astimezone().isoformat(),
            "directory": str(directory.resolve()),
        }, indent=2), encoding="utf-8")
    config.stash[_run_directory] = directory

    if config.option.xmlpath is None:
        config.option.xmlpath = str(directory / "junit.xml")
    if config.pluginmanager.hasplugin("allure_pytest") and config.option.allure_report_dir is None:
        config.option.allure_report_dir = str(directory / "allure-results")
    if config.getoption("--screenshots-dir") is None:
        config.option.screenshots_dir = str(directory / "screenshots")


def _step_summary(steps: list[dict]) -> str:
    lines = []

    def visit(events: list[dict], depth: int) -> None:
        for event in events:
            lines.append(f"{'  ' * depth}{event['status'].upper()}: {event['name']}")
            if "error" in event:
                lines.append(f"{'  ' * (depth + 1)}{event['error']}")
            visit(event["steps"], depth + 1)

    visit(steps, 0)
    return "\n".join(lines)


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
    group.addoption("--browser", default=None,
                    help="Override the configured browser strategy name")
    group.addoption("--headless", action="store_true", default=False,
                    help="Run without a visible browser window")
    group.addoption("--headed", action="store_true", default=False,
                    help="Run with a visible browser window")
    group.addoption("--base-url", default=None, help="Base URL for relative page navigation")
    group.addoption("--reports-root", default="artifacts",
                    help="Root directory for the latest test report")
    group.addoption("--screenshots-dir", default=None,
                    help="Directory for failure screenshots")
    group.addoption("--page-load-timeout", type=float, default=None,
                    help="Override the browser navigation timeout in seconds")
    group.addoption("--action-timeout", type=float, default=None,
                    help="Override the locator action timeout in seconds")
    group.addoption("--assertion-timeout", type=float, default=None,
                    help="Override the retrying assertion timeout in seconds")


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--headless") and config.getoption("--headed"):
        raise pytest.UsageError("Choose either --headless or --headed")

    overrides = {}
    for option, setting in _TIMEOUT_OPTIONS.items():
        value = config.getoption(option)
        if value is None:
            continue
        if not math.isfinite(value) or value < 0:
            raise pytest.UsageError(f"{option} must be a finite, non-negative number")
        overrides[setting] = value

    if isinstance(config, pytest.Config):
        _configure_reports(config)
    config.stash[_previous_timeout_settings] = {
        setting: settings.get(setting) for setting in overrides
    }
    for setting, value in overrides.items():
        settings.set(setting, value)


def pytest_unconfigure(config: pytest.Config) -> None:
    for setting, previous in config.stash.get(_previous_timeout_settings, {}).items():
        settings.set(setting, previous)


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node) -> None:
    """Share the controller's run directory with every xdist worker."""
    node.workerinput["pylenium_run_directory"] = str(node.config.stash[_run_directory])


@pytest.hookimpl(wrapper=True, tryfirst=True)
def pytest_runtest_protocol(item: pytest.Item, nextitem: pytest.Item | None):
    """Keep setup, test and teardown steps in one record per test."""
    step_context = None
    if item.config.pluginmanager.hasplugin("allure_pytest") and item.config.option.allure_report_dir:
        import allure

        step_context = allure.step
    recorder = StepRecorder(step_context=step_context)
    token = install_recorder(recorder)
    try:
        result = yield
    finally:
        try:
            directory = item.config.stash[_run_directory] / "steps"
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f"{uuid4().hex}.json").write_text(json.dumps({
                "test": item.nodeid,
                "steps": recorder.steps,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as error:
            logger.warning("Step report unavailable: %s", error)
        finally:
            reset_recorder(token)
    return result


def pytest_terminal_summary(terminalreporter) -> None:
    """Make the report directory discoverable after a local run."""
    directory = terminalreporter.config.stash.get(_run_directory, None)
    if directory is not None:
        terminalreporter.write_sep("-", f"Pylenium reports: {directory.resolve()}")


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
    recorder = current_recorder()
    if recorder is not None and report.when in ("setup", "call") and recorder.steps:
        summary = _step_summary(recorder.steps)
        report.sections.append(("Pylenium steps", summary))
        if report.when == "call" or report.failed:
            item.user_properties.append(("pylenium_steps", summary))
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

            allure.attach(image, name="Screenshot on failure",
                          attachment_type=allure.attachment_type.PNG)
    except Exception as error:
        diagnostic = f"Failure screenshot unavailable: {type(error).__name__}: {error}"
        report.sections.append(("Screenshot capture error", diagnostic))
        logger.warning(diagnostic)
    return report
