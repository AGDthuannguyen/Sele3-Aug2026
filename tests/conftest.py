"""Shared target for browser tests; the plugin owns browser session cleanup."""

import pytest


@pytest.fixture
def internet_page(browser, pytestconfig):
    """Open The Internet's login page, or a compatible --base-url deployment."""
    base_url = pytestconfig.getoption("--base-url") or "https://the-internet.herokuapp.com/"
    page = browser.new_page(base_url=base_url)
    page.goto("/login")
    return page
