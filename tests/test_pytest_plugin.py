"""Exercise the installed plugin in isolated pytest subprocesses.

The multiline strings below are executable test modules, not commented-out code.
pytester writes them into temporary files and runs the real installed plugin.
Only browser creation is mocked; pytest performs fixture setup and teardown.
"""

from unittest.mock import Mock

import pytest

from pylenium import Browser

pytest_plugins = ["pytester"]


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
