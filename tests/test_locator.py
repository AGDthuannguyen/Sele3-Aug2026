"""Tests for Locator: element finding, auto-wait, child scope, collections."""

import os
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from selenium.common.exceptions import (
    ElementClickInterceptedException, ElementNotInteractableException,
    InvalidArgumentException, InvalidElementStateException, InvalidSelectorException,
    InvalidSessionIdException, NoSuchElementException, StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webelement import WebElement

from pylenium import Browser, Locator
from pylenium.waits.auto_wait import AutoWait


@pytest.fixture(scope="module")
def page():
    """Launch browser and open local test page."""
    browser = Browser.launch(headless=True)
    p = browser.new_page()
    test_html = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "html", "test_page.html")
    )
    p.goto(f"file:///{test_html}")
    yield p
    browser.close()


# -- CSS Selector --

def test_find_by_css(page):
    heading = page.locator("#heading")
    assert heading.text() == "Hello Pylenium"


# -- XPath Selector --

def test_find_by_xpath(page):
    heading = page.locator("//h1[@id='heading']")
    assert heading.text() == "Hello Pylenium"


# -- Auto-wait for delayed element --

def test_auto_wait_for_delayed_element(page):
    delayed = page.locator("#delayed-element")
    assert delayed.text() == "I appeared after 1 second"


# -- Child scope --

def test_child_scope(page):
    container = page.locator("#container")
    first_item = container.locator(".item").first()
    assert first_item.text() == "Item 1"


# -- Collection methods --

def test_all_returns_correct_count(page):
    items = page.locator("#container .item").all()
    assert len(items) == 3


def test_count(page):
    assert page.locator("#container .item").count() == 3


def test_nth(page):
    second_item = page.locator("#container .item").nth(1)
    assert second_item.text() == "Item 2"


def test_first(page):
    first_item = page.locator("#container .item").first()
    assert first_item.text() == "Item 1"


# -- get_by_role --

def test_get_by_role(page):
    button = page.get_by_role("button", name="Submit")
    assert button.text() == "Submit"


# -- get_by_text --

def test_get_by_text(page):
    link = page.get_by_text("Click me")
    assert link.is_visible()


# -- fill --

def test_fill_input(page):
    username = page.locator("#username")
    username.fill("testuser")
    assert username.get_attribute("value") == "testuser"


# -- is_visible --

def test_hidden_element_not_visible(page):
    hidden = page.locator("#hidden-element")
    assert hidden.is_visible() is False


# -- get_attribute --

def test_get_attribute(page):
    username = page.locator("#username")
    assert username.get_attribute("type") == "text"


def test_selector_quotes_dom_execution(page):
    """Test XPath quoting in actual DOM."""
    # Create an element with complex quotes
    page._driver.execute_script("""
        var btn = document.createElement('button');
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-label', `Click 'here' and "there"`);
        btn.innerText = 'Complex Quote Button';
        document.body.appendChild(btn);
    """)

    loc = page.get_by_role("button", name="Click 'here' and \"there\"")
    assert loc.is_visible()

    # Create another element for get_by_text
    page._driver.execute_script("""
        var div = document.createElement('div');
        div.innerText = `Text with 'single' and "double" quotes`;
        document.body.appendChild(div);
    """)

    loc_text = page.get_by_text('Text with \'single\' and "double" quotes')
    assert loc_text.is_visible()


# Focused unit tests for retry boundaries; these do not launch a browser.

@pytest.fixture
def fast_action_waits(monkeypatch):
    config = {"waits.timeout": 0.05, "waits.polling_interval": 0.001}
    monkeypatch.setattr(
        "pylenium.waits.auto_wait.settings",
        SimpleNamespace(get=lambda key, default=None: config.get(key, default)),
    )


def _editable_element():
    element = Mock(spec=WebElement)
    element.tag_name = "input"
    element.is_displayed.return_value = True
    element.is_enabled.return_value = True
    element.get_property.side_effect = lambda name: "text" if name == "type" else False
    element.get_dom_attribute.return_value = None
    element.get_attribute.return_value = None
    element.text = ""
    return element


@pytest.mark.parametrize("stage", ["clear", "send_keys"])
@pytest.mark.parametrize("failure", [
    NoSuchElementException, StaleElementReferenceException,
    ElementNotInteractableException, InvalidElementStateException,
])
def test_fill_retries_entire_operation_on_transient_failure(fast_action_waits, stage, failure):
    driver = Mock()
    first, replacement = _editable_element(), _editable_element()
    getattr(first, stage).side_effect = failure("state changed")
    driver.find_elements.side_effect = [[first], [replacement]]

    Locator("#input", driver=driver).fill("new text")

    assert driver.find_elements.call_count == 2
    replacement.clear.assert_called_once()
    replacement.send_keys.assert_called_once_with("new text")
    if stage == "clear":
        first.send_keys.assert_not_called()


def test_fill_clears_partial_text_before_retry(fast_action_waits):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    contents = {"value": "old", "attempts": 0}

    def clear():
        contents["value"] = ""

    def type_text(text):
        contents["attempts"] += 1
        if contents["attempts"] == 1:
            contents["value"] += text[:2]
            raise ElementNotInteractableException("focus changed")
        contents["value"] += text

    element.clear.side_effect = clear
    element.send_keys.side_effect = type_text
    Locator("#input", driver=driver).fill("hello")
    assert contents["value"] == "hello"
    assert element.clear.call_count == 2


@pytest.mark.parametrize("stage", ["clear", "send_keys"])
@pytest.mark.parametrize("failure", [InvalidArgumentException, InvalidSessionIdException, TypeError])
def test_fill_propagates_non_retryable_errors(fast_action_waits, stage, failure):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    error = failure("do not retry")
    getattr(element, stage).side_effect = error
    with pytest.raises(failure) as caught:
        Locator("#input", driver=driver).fill("value")
    assert caught.value is error
    assert driver.find_elements.call_count == 1


@pytest.mark.parametrize("condition", ["readonly", "disabled", "hidden"])
def test_fill_waits_before_clear(fast_action_waits, condition):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    if condition == "readonly":
        element.get_dom_attribute.side_effect = ["true", None]
    elif condition == "disabled":
        element.is_enabled.side_effect = [False, True]
    else:
        element.is_displayed.side_effect = [False, True]

    Locator("#input", driver=driver).fill("ready")
    assert driver.find_elements.call_count == 2
    element.clear.assert_called_once()
    element.send_keys.assert_called_once_with("ready")


def test_fill_empty_text_only_clears(fast_action_waits):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    Locator("#input", driver=driver).fill("")
    element.clear.assert_called_once()
    element.send_keys.assert_not_called()


@pytest.mark.parametrize("tag,input_type", [("button", None), ("input", "file"), ("input", "checkbox")])
def test_fill_rejects_unsupported_targets(fast_action_waits, tag, input_type):
    driver = Mock()
    element = _editable_element()
    element.tag_name = tag
    element.get_property.side_effect = lambda name: input_type if name == "type" else False
    driver.find_elements.return_value = [element]
    with pytest.raises(ValueError, match="fill"):
        Locator("#unsupported", driver=driver).fill("text")
    assert driver.find_elements.call_count == 1
    element.clear.assert_not_called()


def test_fill_rejects_non_string_before_query():
    driver = Mock()
    with pytest.raises(TypeError, match="string"):
        Locator("#input", driver=driver).fill(None)
    driver.find_elements.assert_not_called()


@pytest.mark.parametrize("failure", [
    ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException,
])
def test_click_retries_transient_failures(fast_action_waits, failure):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    element.click.side_effect = [failure("blocked"), None]
    Locator("#button", driver=driver).click()
    assert driver.find_elements.call_count == 2
    assert element.click.call_count == 2


def test_invalid_selector_is_not_retried(fast_action_waits):
    driver = Mock()
    error = InvalidSelectorException("bad CSS")
    driver.find_elements.side_effect = error
    with pytest.raises(InvalidSelectorException) as caught:
        Locator("[", driver=driver).click()
    assert caught.value is error
    assert driver.find_elements.call_count == 1


def test_read_does_not_retry_interaction_errors(fast_action_waits):
    driver = Mock()
    element = _editable_element()
    driver.find_elements.return_value = [element]
    error = ElementNotInteractableException("unexpected read error")
    element.get_attribute.side_effect = error
    with pytest.raises(ElementNotInteractableException) as caught:
        Locator("#input", driver=driver).get_attribute("value")
    assert caught.value is error
    assert driver.find_elements.call_count == 1


def test_empty_read_results_are_successful(fast_action_waits):
    driver = Mock()
    driver.find_elements.return_value = [_editable_element()]
    locator = Locator("#input", driver=driver)
    assert locator.text() == ""
    assert locator.get_attribute("missing") is None
    assert driver.find_elements.call_count == 2


def test_nth_retries_until_index_exists(fast_action_waits):
    driver = Mock()
    first, second = _editable_element(), _editable_element()
    second.text = "second"
    driver.find_elements.side_effect = [[first], [first, second]]
    assert Locator(".item", driver=driver).nth(1).text() == "second"
    assert driver.find_elements.call_count == 2


def test_child_action_resolves_replaced_parent(fast_action_waits):
    driver = Mock()
    old, new = _editable_element(), _editable_element()
    child = _editable_element()
    child.text = "replacement child"
    old.find_elements.side_effect = StaleElementReferenceException()
    new.find_elements.return_value = [child]
    driver.find_elements.side_effect = [[old], [new]]
    assert Locator("#parent", driver=driver).locator(".child").text() == "replacement child"
    assert driver.find_elements.call_count == 2


def test_action_timeout_reports_scope_and_index(fast_action_waits):
    driver = Mock()
    parent = _editable_element()
    parent.find_elements.return_value = []
    driver.find_elements.return_value = [parent]
    with pytest.raises(TimeoutException) as caught:
        Locator("#parent", driver=driver).locator(".child").nth(3).click()
    message = str(caught.value)
    assert "#parent" in message and ".child" in message and "index=3" in message


@pytest.mark.parametrize("child_appears_at", [9, 16])
def test_nested_locator_shares_one_timeout(monkeypatch, child_appears_at):
    """Parent at 8s must not restart the 10s budget for its child."""
    clock = SimpleNamespace(now=0.0)

    def advance(seconds):
        clock.now += seconds

    # Run Selenium's real polling loop with a deterministic clock and no sleep.
    monkeypatch.setattr(import_module("selenium.webdriver.support.wait"), "time",
                        SimpleNamespace(monotonic=lambda: clock.now, sleep=advance))
    config = {"waits.timeout": 10, "waits.polling_interval": 0.5}
    monkeypatch.setattr("pylenium.waits.auto_wait.settings",
                        SimpleNamespace(get=lambda key, default=None: config.get(key, default)))
    driver = Mock()
    parent, child = _editable_element(), _editable_element()
    child.get_attribute.return_value = "ready"
    driver.find_elements.side_effect = lambda *_: [parent] if clock.now >= 8 else []
    parent.find_elements.side_effect = lambda *_: [child] if clock.now >= child_appears_at else []
    locator = Locator("#parent", driver=driver).locator(".child")

    if child_appears_at < 10:
        assert locator.get_attribute("data-state") == "ready"
        assert clock.now == 9
    else:
        with pytest.raises(TimeoutException):
            locator.get_attribute("data-state")
        assert 10 <= clock.now < 11
        child.get_attribute.assert_not_called()


@pytest.mark.parametrize("timeout", [0, 0.001])
def test_custom_ignore_keeps_selenium_missing_default(timeout):
    predicate = Mock(side_effect=NoSuchElementException("missing"))
    with pytest.raises(TimeoutException):
        AutoWait(Mock(), timeout=timeout, polling=0.001, ignored_exceptions=()).until(predicate)
    assert predicate.call_count >= 1


# Browser checks cover editable state and real clear/send_keys behavior.

@pytest.mark.parametrize("tag", ["input", "textarea", "div"])
def test_fill_replaces_real_editable_content(page, tag):
    page._driver.execute_script("""
        const element = document.createElement(arguments[0]);
        element.id = 'fill-contract';
        if (arguments[0] === 'div') {
            element.contentEditable = 'true';
            element.textContent = 'old';
        } else {
            element.value = 'old';
        }
        document.body.appendChild(element);
    """, tag)
    try:
        locator = page.locator("#fill-contract")
        locator.fill("replacement")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == "replacement"
        locator.fill("")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == ""
    finally:
        page._driver.execute_script("document.getElementById('fill-contract')?.remove();")


def test_fill_waits_for_real_readonly_input(page):
    page._driver.execute_script("""
        const input = document.createElement('input');
        input.id = 'readonly-contract';
        input.value = 'old';
        input.readOnly = true;
        document.body.appendChild(input);
        setTimeout(() => { input.readOnly = false; }, 400);
    """)
    try:
        locator = page.locator("#readonly-contract")
        locator.fill("ready")
        assert locator.get_attribute("value") == "ready"
    finally:
        page._driver.execute_script("document.getElementById('readonly-contract')?.remove();")
