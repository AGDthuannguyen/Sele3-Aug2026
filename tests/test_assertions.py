"""Tests for expect() assertions: LocatorAssertions and PageAssertions."""

from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock

import pytest
from selenium.common.exceptions import (
    ElementNotInteractableException, InvalidSelectorException,
    InvalidSessionIdException, StaleElementReferenceException, TimeoutException,
)
from selenium.webdriver.remote.webelement import WebElement

from pylenium import Locator, Page, expect


# Unit tests for the assertion contract, separate from browser setup.

@pytest.fixture
def fast_assertion_settings(monkeypatch):
    config = {"assertions.timeout": 0.02, "assertions.polling_interval": 0.001}
    module = import_module("pylenium.assertions.expect")
    monkeypatch.setattr(
        module, "settings",
        SimpleNamespace(get=lambda key, default=None: config.get(key, default)),
    )
    return config


ASSERTION_CASES = [
    ("to_be_visible", (), "is_displayed", True, False),
    ("to_be_enabled", (), "is_enabled", True, False),
    ("to_have_text", ("wanted",), "text", "wanted text", "other text"),
    ("to_have_attribute", ("data-state", "wanted"), "get_attribute", "wanted", "other"),
]


def _set_observation(element, accessor, *, value=None, error=None):
    if accessor == "text":
        type(element).text = PropertyMock(return_value=value, side_effect=error)
    else:
        method = getattr(element, accessor)
        method.return_value = value
        method.side_effect = error


@pytest.mark.parametrize("method,args,accessor,matching,different", ASSERTION_CASES)
@pytest.mark.parametrize("negated", [False, True])
@pytest.mark.parametrize("replacement_passes", [False, True])
def test_assertion_retries_stale_before_deciding(
    fast_assertion_settings, method, args, accessor, matching, different, negated, replacement_passes,
):
    driver = Mock()
    stale, replacement = Mock(spec=WebElement), Mock(spec=WebElement)
    _set_observation(stale, accessor, error=StaleElementReferenceException("replaced"))
    value = different if negated == replacement_passes else matching
    _set_observation(replacement, accessor, value=value)
    driver.find_elements.side_effect = lambda *_: (
        [stale] if driver.find_elements.call_count == 1 else [replacement]
    )
    assertion = expect(Locator("#target", driver=driver))
    if negated:
        assertion = assertion.not_

    if replacement_passes:
        getattr(assertion, method)(*args)
        assert driver.find_elements.call_count == 2
    else:
        with pytest.raises(AssertionError):
            getattr(assertion, method)(*args)
        assert driver.find_elements.call_count >= 2


@pytest.mark.parametrize("method,args,accessor,matching,different", ASSERTION_CASES)
@pytest.mark.parametrize("negated", [False, True])
def test_missing_element_uses_each_assertions_contract(
    fast_assertion_settings, method, args, accessor, matching, different, negated,
):
    driver = Mock()
    driver.find_elements.return_value = []
    assertion = expect(Locator("#missing", driver=driver), timeout=0)
    if negated:
        assertion = assertion.not_
    if method == "to_be_visible" and negated:
        getattr(assertion, method)(*args)
    else:
        with pytest.raises(AssertionError, match="missing|NoSuchElementException"):
            getattr(assertion, method)(*args)
    assert driver.find_elements.call_count == 1


@pytest.mark.parametrize("failure", [
    TypeError, InvalidSelectorException, InvalidSessionIdException,
    ElementNotInteractableException, TimeoutException,
])
@pytest.mark.parametrize("negated", [False, True])
def test_assertion_does_not_retry_unexpected_driver_errors(fast_assertion_settings, failure, negated):
    driver = Mock()
    error = failure("original error")
    driver.find_elements.side_effect = error
    assertion = expect(Locator("#target", driver=driver))
    if negated:
        assertion = assertion.not_
    with pytest.raises(failure) as caught:
        assertion.to_be_visible()
    assert caught.value is error
    assert driver.find_elements.call_count == 1


def test_missing_attribute_is_different_from_missing_element(fast_assertion_settings):
    driver = Mock()
    element = Mock(spec=WebElement)
    element.get_attribute.return_value = None
    driver.find_elements.return_value = [element]
    expect(Locator("#target", driver=driver), timeout=0).not_.to_have_attribute("data-x", "value")
    assert driver.find_elements.call_count == 1


def test_assertion_failure_preserves_scope_and_last_value(fast_assertion_settings):
    driver = Mock()
    parent, child = Mock(spec=WebElement), Mock(spec=WebElement)
    child.is_enabled.return_value = True
    driver.find_elements.return_value = [parent]
    parent.find_elements.return_value = [child, child]
    locator = Locator("#parent", driver=driver).locator(".child").nth(1)
    with pytest.raises(AssertionError) as caught:
        expect(locator, timeout=0).not_.to_be_enabled()
    message = str(caught.value)
    assert "#parent" in message and ".child" in message and "index=1" in message
    assert "Last state: enabled=True" in message
    assert driver.find_elements.call_count == 1
    assert parent.find_elements.call_count == 1


@pytest.mark.parametrize("target_type", ["locator", "page"])
def test_negation_preserves_settings_without_mutating_original(fast_assertion_settings, target_type):
    driver = Mock()
    target = Locator("#target", driver=driver) if target_type == "locator" else Page(driver)
    original = expect(target, timeout=0)
    original_wait = original._wait
    fast_assertion_settings["assertions.timeout"] = 99
    fast_assertion_settings["assertions.polling_interval"] = 99
    negated = original.not_
    assert negated is not original
    assert negated._wait is original_wait
    assert not original._is_negated
    assert negated._is_negated
    assert not negated.not_._is_negated


@pytest.mark.parametrize("method,property_name", [("to_have_title", "title"), ("to_have_url", "current_url")])
@pytest.mark.parametrize("negated", [False, True])
def test_page_assertions_keep_substring_semantics(fast_assertion_settings, method, property_name, negated):
    driver = Mock()
    setattr(driver, property_name, "prefix wanted suffix")
    assertion = expect(Page(driver), timeout=0)
    if negated:
        assertion = assertion.not_
    getattr(assertion, method)("absent" if negated else "wanted")


@pytest.mark.parametrize("timeout", [0, 0.01])
def test_autowait_zero_and_positive_timeouts_respect_exception_policy(timeout):
    from pylenium.waits.auto_wait import AutoWait
    driver = Mock()
    error = ElementNotInteractableException("not retryable for reads")
    predicate = Mock(side_effect=error)
    wait = AutoWait(driver, timeout=timeout, polling=0.001,
                    ignored_exceptions=(StaleElementReferenceException,))
    with pytest.raises(ElementNotInteractableException) as caught:
        wait.until(predicate)
    assert caught.value is error
    predicate.assert_called_once_with(driver)
