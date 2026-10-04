"""Phase 4 checks using The Internet's LoginPage and URLs.

WebDriver is mocked here to verify readiness failures and navigation arguments.
Real website behavior is exercised in test_internet.py. These checks may be
replaced or removed when they no longer serve a later phase's acceptance scope.
"""

from unittest.mock import Mock
from types import SimpleNamespace

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException

from pages.login_page import LoginPage
from pylenium import Page


BASE_URL = "https://the-internet.herokuapp.com"


def test_page_object_is_lazy_and_open_returns_self():
    driver = Mock()
    element = Mock()
    element.is_displayed.return_value = True
    driver.find_elements.return_value = [element]
    model = LoginPage(Page(driver, base_url=BASE_URL))
    driver.find_elements.assert_not_called()
    assert model.open() is model
    driver.find_elements.assert_not_called()
    assert model.wait_until_loaded(timeout=0) is model
    driver.get.assert_called_once_with(f"{BASE_URL}/login")


def test_readiness_timeout_and_unexpected_error():
    model = LoginPage(Page(Mock(), base_url=BASE_URL))
    model.is_loaded = Mock(side_effect=NoSuchElementException())
    with pytest.raises(TimeoutException):
        model.wait_until_loaded(timeout=0)
    model.is_loaded.assert_called_once()
    model.is_loaded.side_effect = TypeError("bug")
    with pytest.raises(TypeError, match="bug"):
        model.wait_until_loaded(timeout=0)


def test_readiness_retries(monkeypatch):
    config = {"waits.polling_interval": 0.001}
    monkeypatch.setattr(
        "pylenium.waits.auto_wait.settings",
        SimpleNamespace(get=lambda key, default=None: config.get(key, default)),
    )
    model = LoginPage(Page(Mock(), base_url=BASE_URL))
    model.is_loaded = Mock(side_effect=[NoSuchElementException(), False, True])
    assert model.wait_until_loaded(timeout=2) is model
    assert model.is_loaded.call_count == 3


def test_empty_url_rejected_before_navigation():
    driver = Mock()
    model = LoginPage(Page(driver, base_url=BASE_URL))
    model.URL = ""
    with pytest.raises(ValueError):
        model.open()
    driver.get.assert_not_called()


@pytest.mark.parametrize("url,expected", [
    ("1", f"{BASE_URL}/dynamic_loading/1"),
    ("/login", f"{BASE_URL}/login"),
    (f"{BASE_URL}/checkboxes", f"{BASE_URL}/checkboxes"),
    ("//the-internet.herokuapp.com/login", f"{BASE_URL}/login"),
])
def test_navigation_uses_standard_url_resolution(url, expected):
    driver = Mock()
    Page(driver, base_url=f"{BASE_URL}/dynamic_loading/").goto(url)
    driver.get.assert_called_once_with(expected)


def test_screenshot_saves_the_same_capture(tmp_path):
    driver = Mock()
    driver.get_screenshot_as_png.return_value = b"png"
    destination = tmp_path / "capture.png"
    assert Page(driver).screenshot(str(destination)) == destination.read_bytes() == b"png"
    driver.get_screenshot_as_png.assert_called_once()


def test_screenshot_can_return_bytes_without_a_file():
    driver = Mock()
    driver.get_screenshot_as_png.return_value = b"png"
    assert Page(driver).screenshot() == b"png"
    driver.get_screenshot_as_png.assert_called_once()
