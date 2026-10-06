"""Browser integration tests against The Internet.

Network failures remain failures, not skips. Injected elements below exercise
browser edge cases that the site's built-in examples do not supply.
"""

import pytest

from pages.login_page import LoginPage
from pylenium import expect

pytestmark = pytest.mark.browser

# Public-site redirects can outlast the framework's short assertion default.
LOGIN_RESPONSE_TIMEOUT = 60


def test_login_form_locators_and_assertions(internet_page):
    login = LoginPage(internet_page).wait_until_loaded(timeout=5)
    assert internet_page.locator("//h2").text() == "Login Page"
    assert internet_page.get_by_text("Login Page").is_visible()
    username = internet_page.locator("#username")
    expect(username).to_be_visible()
    expect(username).to_be_enabled()
    expect(username).to_have_attribute("type", "text")
    expect(internet_page).to_have_title("The Internet")
    expect(internet_page).to_have_url("/login")
    expect(internet_page).not_.to_have_title("Wrong Title")
    expect(internet_page.locator("#does-not-exist")).not_.to_be_visible()


def test_login_success(internet_page):
    login = LoginPage(internet_page).wait_until_loaded(timeout=5)
    login.login("tomsmith", "SuperSecretPassword!")
    expect(internet_page, timeout=LOGIN_RESPONSE_TIMEOUT).to_have_url("/secure")
    expect(internet_page.locator("#flash")).to_have_text("You logged into a secure area!")


def test_login_rejects_invalid_password(internet_page):
    login = LoginPage(internet_page).wait_until_loaded(timeout=5)
    login.login("tomsmith", "invalid-password")
    expect(internet_page.locator("#flash"), timeout=LOGIN_RESPONSE_TIMEOUT).to_have_text(
        "Your password is invalid!"
    )
    expect(internet_page).to_have_url("/login")


@pytest.mark.parametrize("example", [1, 2])
def test_dynamic_loading_waits_for_hidden_or_missing_child(internet_page, example):
    internet_page.goto(f"/dynamic_loading/{example}")
    result = internet_page.locator("#finish").locator("h4")
    expect(result).not_.to_be_visible()
    internet_page.locator("#start button").click()
    assert result.text() == "Hello World!"
    expect(result).to_be_visible()


def test_dynamic_controls_enable_before_fill(internet_page):
    internet_page.goto("/dynamic_controls")
    field = internet_page.locator("#input-example input")
    expect(field).not_.to_be_enabled()
    internet_page.locator("#input-example button").click()
    field.fill("ready")
    expect(field).to_be_enabled()
    expect(field).to_have_attribute("value", "ready")


def test_child_collections(internet_page):
    internet_page.goto("/checkboxes")
    fields = internet_page.locator("#checkboxes").locator("input")
    assert fields.count() == 2
    assert len(fields.all()) == 2
    assert fields.first().get_attribute("checked") is None
    assert fields.nth(1).get_attribute("checked") == "true"


def test_selector_quotes_dom_execution(internet_page):
    """Test XPath quoting in actual DOM."""
    # Create an element with complex quotes
    internet_page._driver.execute_script("""
        var btn = document.createElement('button');
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-label', `Click 'here' and "there"`);
        btn.innerText = 'Complex Quote Button';
        document.body.appendChild(btn);
    """)

    loc = internet_page.get_by_role("button", name="Click 'here' and \"there\"")
    assert loc.is_visible()

    # Create another element for get_by_text
    internet_page._driver.execute_script("""
        var div = document.createElement('div');
        div.innerText = `Text with 'single' and "double" quotes`;
        document.body.appendChild(div);
    """)

    loc_text = internet_page.get_by_text('Text with \'single\' and "double" quotes')
    assert loc_text.is_visible()


# Browser checks cover editable state and real clear/send_keys behavior.

@pytest.mark.parametrize("tag", ["input", "textarea", "div"])
def test_fill_replaces_real_editable_content(internet_page, tag):
    internet_page._driver.execute_script("""
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
        locator = internet_page.locator("#fill-contract")
        locator.fill("replacement")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == "replacement"
        locator.fill("")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == ""
    finally:
        internet_page._driver.execute_script("document.getElementById('fill-contract')?.remove();")


def test_fill_waits_for_real_readonly_input(internet_page):
    internet_page._driver.execute_script("""
        const input = document.createElement('input');
        input.id = 'readonly-contract';
        input.value = 'old';
        input.readOnly = true;
        document.body.appendChild(input);
        setTimeout(() => { input.readOnly = false; }, 400);
    """)
    try:
        locator = internet_page.locator("#readonly-contract")
        locator.fill("ready")
        assert locator.get_attribute("value") == "ready"
    finally:
        internet_page._driver.execute_script("document.getElementById('readonly-contract')?.remove();")
