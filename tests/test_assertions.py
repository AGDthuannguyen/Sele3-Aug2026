"""Tests for expect() assertions: LocatorAssertions and PageAssertions."""

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


# -- LocatorAssertions --

def test_to_have_text(page):
    heading = page.locator("#heading")
    expect(heading).to_have_text("Hello Pylenium")


def test_to_be_visible(page):
    heading = page.locator("#heading")
    expect(heading).to_be_visible()


def test_not_to_be_visible(page):
    hidden = page.locator("#hidden-element")
    expect(hidden).not_.to_be_visible()


def test_to_be_enabled(page):
    username = page.locator("#username")
    expect(username).to_be_enabled()


def test_to_have_attribute(page):
    username = page.locator("#username")
    expect(username).to_have_attribute("type", "text")


def test_assertion_timeout_raises_error(page):
    nonexistent = page.locator("#does-not-exist")
    with pytest.raises(AssertionError):
        expect(nonexistent).to_be_visible()


# -- PageAssertions --

def test_page_to_have_title(page):
    expect(page).to_have_title("Pylenium Test Page")


def test_page_to_have_url(page):
    expect(page).to_have_url("test_page.html")


def test_page_not_to_have_title(page):
    expect(page).not_.to_have_title("Wrong Title")
