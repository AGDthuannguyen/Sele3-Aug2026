"""Shared target for browser tests; the plugin owns browser session cleanup."""

import pytest


@pytest.fixture
def practice_page(browser, pytestconfig):
    """Open the selected public practice site's login page."""
    base_url = pytestconfig.getoption("--base-url") or "https://www.automationexercise.com/"
    page = browser.new_page(base_url=base_url)
    page.goto("/login")
    return page
