"""Exercise the installed plugin in isolated pytest subprocesses.

The multiline strings below are executable test modules, not commented-out code.
pytester writes them into temporary files and runs the real installed plugin.
Only browser creation is mocked; pytest performs fixture setup and teardown.
"""

from unittest.mock import Mock
import json
from types import SimpleNamespace
from xml.etree import ElementTree

import pytest

from pylenium import Browser
from pylenium.plugins.pytest_plugin import _reporting_request_timeout

pytest_plugins = ["pytester"]


@pytest.mark.parametrize("fails", [False, True])
def test_reporting_timeout_is_restored(fails):
    config = SimpleNamespace(timeout=None)
    driver = Mock()
    driver.command_executor.client_config = config
    try:
        with _reporting_request_timeout(Browser(driver)):
            assert config.timeout == 10
            if fails:
                raise RuntimeError("capture error")
    except RuntimeError:
        assert fails
    assert config.timeout is None


@pytest.mark.parametrize("scenario", ["pass", "test_failure", "page_failure", "navigation_failure"])
def test_real_fixture_cleanup_and_isolation(pytester, scenario):
    pytester.makeconftest('''
import pytest
from unittest.mock import Mock
from pylenium.core.browser import Browser

instances = []

@pytest.fixture(autouse=True)
def mock_launch(monkeypatch):
    def launch(**kwargs):
        session = Mock()
        instances.append(session)
        if SCENARIO == "navigation_failure":
            session.new_page.return_value.goto.side_effect = RuntimeError("navigation failed")
        if SCENARIO == "page_failure":
            session.new_page.side_effect = RuntimeError("page failed")
        return session
    monkeypatch.setattr(Browser, "launch", launch)

@pytest.fixture
def navigated(page):
    page.goto("/example")
    return page

def pytest_sessionfinish(session):
    assert len(instances) == 2
    assert instances[0] is not instances[1]
    for instance in instances:
        instance.close.assert_called_once_with()
'''.replace("SCENARIO", repr(scenario)))
    pytester.makepyfile('''
def test_one(navigated):
    assert SCENARIO != "test_failure"
def test_two(navigated):
    assert SCENARIO != "test_failure"
'''.replace("SCENARIO", repr(scenario)))
    result = pytester.runpytest_subprocess("-q")
    expected = {
        "pass": {"passed": 2},
        "test_failure": {"failed": 2},
        "page_failure": {"errors": 2},
        "navigation_failure": {"errors": 2},
    }[scenario]
    result.assert_outcomes(**expected)
    assert result.ret == (0 if scenario == "pass" else 1)


@pytest.mark.parametrize("flags,headless", [([], None), (["--headless"], True), (["--headed"], False)])
def test_cli_overrides_without_global_mutation(pytester, flags, headless):
    pytester.makeconftest('''
import pytest
from unittest.mock import Mock
from pylenium.core.browser import Browser
from pylenium.config.config import settings

@pytest.fixture(autouse=True)
def launch(monkeypatch):
    before = settings.get("browser.type")
    factory = Mock(return_value=Mock())
    monkeypatch.setattr(Browser, "launch", factory)
    yield
    factory.assert_called_once_with(browser_type="firefox", headless=HEADLESS)
    factory.return_value.new_page.assert_called_once_with(base_url="https://example.org")
    assert settings.get("browser.type") == before
'''.replace("HEADLESS", repr(headless)))
    pytester.makepyfile("def test_page(page): pass")
    pytester.runpytest_subprocess("-q", "--browser=firefox", "--base-url=https://example.org", *flags).assert_outcomes(passed=1)


def test_external_browser_strategy_via_cli_and_fixture(pytester):
    pytester.makeconftest('''
from unittest.mock import Mock
from pylenium.core.browser_strategy import BROWSER_STRATEGIES, ChromeStrategy

created = []

class ConsumerStrategy(ChromeStrategy):
    def create_driver(self, options):
        driver = Mock()
        created.append(driver)
        return driver

BROWSER_STRATEGIES["consumer_browser"] = ConsumerStrategy

def pytest_sessionfinish(session):
    assert len(created) == 1
    created[0].quit.assert_called_once_with()
''')
    pytester.makepyfile('''
def test_consumer_browser(browser, page):
    assert page._driver is browser._driver
    page.goto("https://www.automationexercise.com/login")
    browser._driver.get.assert_called_once_with("https://www.automationexercise.com/login")
''')
    pytester.runpytest_subprocess("-q", "--browser=consumer_browser").assert_outcomes(passed=1)


def test_unknown_browser_is_validated_at_launch(pytester):
    pytester.makepyfile("def test_browser(browser): pass")
    result = pytester.runpytest_subprocess("-q", "--browser=not_registered")
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*Unsupported browser type: 'not_registered'*"])


def test_conflicting_cli_options_fail(pytester):
    pytester.makepyfile("def test_unused(): pass")
    result = pytester.runpytest_subprocess("--headless", "--headed")
    assert result.ret == 4
    result.stderr.fnmatch_lines(["*Choose either --headless or --headed*"])


def test_plugin_does_not_launch_for_unit_tests(pytester):
    pytester.makeconftest('''
import pytest
from unittest.mock import Mock
from pylenium.core.browser import Browser

@pytest.fixture(autouse=True)
def forbid_launch(monkeypatch):
    factory = Mock(side_effect=AssertionError("unexpected browser launch"))
    monkeypatch.setattr(Browser, "launch", factory)
    yield
    factory.assert_not_called()
''')
    pytester.makepyfile("def test_unit(): assert 1 + 1 == 2")
    pytester.runpytest_subprocess("-q").assert_outcomes(passed=1)


@pytest.mark.parametrize("cleanup_fails", [False, True])
def test_launch_cleans_up_failed_configuration(monkeypatch, cleanup_fails):
    driver = Mock()
    setup_error = RuntimeError("setup")
    cleanup_error = RuntimeError("cleanup")
    driver.set_page_load_timeout.side_effect = setup_error
    if cleanup_fails:
        driver.quit.side_effect = cleanup_error
    monkeypatch.setattr("pylenium.core.browser.BrowserFactory.create", Mock(return_value=driver))
    with pytest.raises(RuntimeError) as caught:
        Browser.launch()
    assert caught.value is setup_error
    if cleanup_fails:
        assert caught.value.__cause__ is cleanup_error
    driver.quit.assert_called_once()


@pytest.mark.parametrize("scenario", [
    "pass", "call", "setup", "closed", "capture_error", "no_browser", "disabled", "attachment_error",
])
def test_failure_screenshots_preserve_result_and_cleanup(pytester, scenario):
    pytester.makeconftest('''
import pytest
from unittest.mock import Mock
from selenium.common.exceptions import InvalidSessionIdException
from pylenium import Browser
from types import SimpleNamespace

@pytest.fixture(autouse=True)
def fake_browser(monkeypatch):
    driver = Mock()
    driver.get_screenshot_as_png.return_value = b"test-png"
    if SCENARIO == "closed":
        driver.get_screenshot_as_png.side_effect = InvalidSessionIdException("closed")
    if SCENARIO == "capture_error":
        driver.get_screenshot_as_png.side_effect = RuntimeError("capture failed")
    factory = Mock(return_value=Browser(driver))
    monkeypatch.setattr(Browser, "launch", factory)
    if SCENARIO == "disabled":
        monkeypatch.setattr("pylenium.plugins.pytest_plugin.settings", SimpleNamespace(get=lambda key, default=None: False))
    if SCENARIO == "attachment_error":
        import allure
        monkeypatch.setattr(allure, "attach", Mock(side_effect=RuntimeError("attachment failed")))
    yield
    if SCENARIO == "no_browser":
        factory.assert_not_called()
        driver.quit.assert_not_called()
    else:
        driver.quit.assert_called_once()
    assert driver.get_screenshot_as_png.call_count == (0 if SCENARIO in ("pass", "no_browser", "disabled") else 1)

@pytest.fixture
def prepared(page):
    if SCENARIO == "setup":
        raise ValueError("original setup failure")
    return page
'''.replace("SCENARIO", repr(scenario)))
    fixture = "" if scenario == "no_browser" else "prepared"
    pytester.makepyfile(f'def test_example({fixture}):\n    assert {scenario == "pass"!r}, "original test failure"')
    result = pytester.runpytest_subprocess(
        "-q", "--alluredir=results", "--screenshots-dir=shots", "--junitxml=result.xml",
    )
    result.assert_outcomes(**({"passed": 1} if scenario == "pass" else
                             {"errors": 1} if scenario == "setup" else {"failed": 1}))
    assert result.ret == (0 if scenario == "pass" else 1)
    screenshots = list((pytester.path / "shots").glob("*.png"))
    assert len(screenshots) == (1 if scenario in ("call", "setup", "attachment_error") else 0)
    records = [json.loads(path.read_text()) for path in (pytester.path / "results").glob("*-result.json")]
    assert len(records) == 1
    attachments = records[0].get("attachments", [])
    pngs = [entry for entry in attachments if entry["type"] == "image/png"]
    assert len(pngs) == (1 if scenario in ("call", "setup") else 0)
    if pngs:
        assert (pytester.path / "results" / pngs[0]["source"]).read_bytes() == b"test-png"
    if scenario in ("closed", "capture_error", "attachment_error"):
        result.stdout.fnmatch_lines(["*Failure screenshot unavailable:*"])


def test_parallel_failures_keep_sessions_and_artifacts_separate(pytester):
    pytester.makeconftest("""
from pathlib import Path
from unittest.mock import Mock

import pytest

from pylenium import Browser


@pytest.fixture(autouse=True)
def fake_browser(monkeypatch, request, worker_id):
    driver = Mock()
    driver.get_screenshot_as_png.return_value = request.node.name.encode()
    def close():
        Path("closed").mkdir(exist_ok=True)
        (Path("closed") / request.node.name).write_text(worker_id)
    driver.quit.side_effect = close
    monkeypatch.setattr(Browser, "launch", Mock(return_value=Browser(driver)))
    yield
    driver.quit.assert_called_once_with()
""")
    pytester.makepyfile("""
import pytest


@pytest.mark.parametrize("case", range(4))
def test_failure(browser, case):
    assert False, f"failure {case}"
""")
    result = pytester.runpytest_subprocess(
        "-q", "-n", "2", "--screenshots-dir=shots",
        "--alluredir=results", "--junitxml=result.xml",
    )
    result.assert_outcomes(failed=4)
    assert result.ret == 1

    closed = list((pytester.path / "closed").iterdir())
    assert len(closed) == 4
    assert {path.read_text() for path in closed} == {"gw0", "gw1"}
    screenshots = list((pytester.path / "shots").glob("*.png"))
    assert len(screenshots) == 4
    assert {path.read_bytes() for path in screenshots} == {
        f"test_failure[{case}]".encode() for case in range(4)
    }
    records = [json.loads(path.read_text()) for path in (pytester.path / "results").glob("*-result.json")]
    assert len(records) == 4
    assert all(any(item["type"] == "image/png" for item in record.get("attachments", []))
               for record in records)
    assert len(list(ElementTree.parse(pytester.path / "result.xml").iter("failure"))) == 4
