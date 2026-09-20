"""Tests for Locator: element finding, auto-wait, child scope, collections."""

import os

import pytest

from pylenium import Browser, expect


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
