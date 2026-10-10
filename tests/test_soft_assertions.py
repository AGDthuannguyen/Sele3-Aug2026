"""Behavioral tests for the separate soft assertion API."""

from unittest.mock import Mock

import pytest
from selenium.common.exceptions import InvalidSessionIdException

from pylenium import Locator, Page, expect, soft_assertions


def test_soft_assertions_collect_multiple_locator_and_page_failures():
    driver = Mock()
    driver.find_elements.return_value = []
    driver.title = "Landing"
    driver.current_url = "https://example.test/landing"
    missing = Locator("#missing", driver=driver)
    page = Page(driver)

    with pytest.raises(AssertionError) as caught:
        with soft_assertions() as soft:
            soft.check(expect(missing, timeout=0).to_be_visible)
            soft.check(expect(page, timeout=0).to_have_title, "Dashboard")
            soft.check(expect(page, timeout=0).to_have_url, "landing")

    message = str(caught.value)
    assert "2 soft assertion(s) failed" in message
    assert "1. Expected Locator" in message
    assert "2. Expected page title" in message
    assert "Last state: missing" in message
    assert driver.find_elements.call_count == 1


def test_soft_assertions_preserve_negative_assertion_semantics():
    driver = Mock()
    driver.find_elements.return_value = []
    missing = Locator("#missing", driver=driver)

    with pytest.raises(AssertionError) as caught:
        with soft_assertions() as soft:
            soft.check(expect(missing, timeout=0).not_.to_be_visible)
            soft.check(expect(missing, timeout=0).not_.to_be_enabled)

    assert "1 soft assertion(s) failed" in str(caught.value)
    assert "enabled=False" in str(caught.value)
    assert driver.find_elements.call_count == 2


def test_soft_assertions_preserve_unexpected_driver_error():
    driver = Mock()
    error = InvalidSessionIdException("session ended")
    driver.find_elements.side_effect = error
    missing = Locator("#missing", driver=driver)

    def earlier_failure():
        raise AssertionError("earlier failure")

    with pytest.raises(InvalidSessionIdException) as caught:
        with soft_assertions() as soft:
            soft.check(earlier_failure)
            soft.check(expect(missing, timeout=0).to_be_visible)

    assert caught.value is error
    assert driver.find_elements.call_count == 1


def test_soft_assertions_pass_args_and_kwargs_and_allow_empty_block():
    assertion = Mock()

    with soft_assertions() as soft:
        soft.check(assertion, "value", required=True)

    assertion.assert_called_once_with("value", required=True)

    with soft_assertions():
        pass
