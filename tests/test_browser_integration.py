"""Browser integration tests against Automation Exercise.

Network failures remain failures, not skips. Injected elements below exercise
browser edge cases that the site's built-in examples do not supply.
"""

import pytest

from pages.login_page import LoginPage
from pylenium import expect

pytestmark = pytest.mark.browser

# Public-site responses can outlast the framework's short assertion default.
LOGIN_RESPONSE_TIMEOUT = 60


def test_login_form_locators_and_assertions(practice_page):
    LoginPage(practice_page).wait_until_loaded(timeout=5)
    assert practice_page.get_by_text("Login to your account").is_visible()
    email = practice_page.locator("[data-qa='login-email']")
    expect(email).to_be_visible()
    expect(email).to_be_enabled()
    expect(email).to_have_attribute("type", "email")
    expect(practice_page).to_have_url("/login")
    expect(practice_page).not_.to_have_title("Wrong Title")
    expect(practice_page.locator("#does-not-exist")).not_.to_be_visible()


def test_page_object_opens_login_form(practice_page):
    practice_page.goto("/")
    login = LoginPage(practice_page).open().wait_until_loaded(timeout=5)
    assert login.is_loaded()
    expect(practice_page).to_have_url("/login")


def test_login_rejects_unknown_account(practice_page):
    login = LoginPage(practice_page).wait_until_loaded(timeout=5)
    login.login("pylenium-unknown@example.invalid", "invalid-password")
    expect(practice_page.get_by_text("Your email or password is incorrect!"),
           timeout=LOGIN_RESPONSE_TIMEOUT).to_be_visible()
    expect(practice_page).to_have_url("/login")


def test_nested_locator_waits_for_parent_and_child(practice_page):
    practice_page._driver.execute_script("""
        setTimeout(() => {
            const parent = document.createElement('div');
            parent.id = 'delayed-parent';
            document.body.appendChild(parent);
            setTimeout(() => {
                const child = document.createElement('span');
                child.className = 'delayed-child';
                child.textContent = 'ready';
                parent.appendChild(child);
            }, 200);
        }, 200);
    """)
    result = practice_page.locator("#delayed-parent").locator(".delayed-child")
    expect(result).not_.to_be_visible()
    assert result.text() == "ready"
    expect(result).to_be_visible()


def test_dynamic_controls_enable_before_fill(practice_page):
    practice_page._driver.execute_script("""
        const field = document.createElement('input');
        field.id = 'delayed-enabled';
        field.disabled = true;
        document.body.appendChild(field);
        setTimeout(() => { field.disabled = false; }, 300);
    """)
    field = practice_page.locator("#delayed-enabled")
    expect(field).not_.to_be_enabled()
    field.fill("ready")
    expect(field).to_be_enabled()
    expect(field).to_have_attribute("value", "ready")


def test_child_collections(practice_page):
    fields = practice_page.locator(".login-form form").locator("input[data-qa]")
    assert fields.count() == 2
    assert len(fields.all()) == 2
    assert fields.first().get_attribute("data-qa") == "login-email"
    assert fields.nth(1).get_attribute("data-qa") == "login-password"


def test_selector_quotes_dom_execution(practice_page):
    """Test XPath quoting in actual DOM."""
    # Create an element with complex quotes
    practice_page._driver.execute_script("""
        var btn = document.createElement('button');
        btn.setAttribute('role', 'button');
        btn.setAttribute('aria-label', `Click 'here' and "there"`);
        btn.innerText = 'Complex Quote Button';
        document.body.appendChild(btn);
    """)

    loc = practice_page.get_by_role("button", name="Click 'here' and \"there\"")
    assert loc.is_visible()

    # Create another element for get_by_text
    practice_page._driver.execute_script("""
        var div = document.createElement('div');
        div.innerText = `Text with 'single' and "double" quotes`;
        document.body.appendChild(div);
    """)

    loc_text = practice_page.get_by_text('Text with \'single\' and "double" quotes')
    assert loc_text.is_visible()


# Browser checks cover editable state and real clear/send_keys behavior.

@pytest.mark.parametrize("tag", ["input", "textarea", "div"])
def test_fill_replaces_real_editable_content(practice_page, tag):
    practice_page._driver.execute_script("""
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
        locator = practice_page.locator("#fill-contract")
        locator.fill("replacement")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == "replacement"
        locator.fill("")
        actual = locator.text() if tag == "div" else locator.get_attribute("value")
        assert actual == ""
    finally:
        practice_page._driver.execute_script("document.getElementById('fill-contract')?.remove();")


def test_fill_waits_for_real_readonly_input(practice_page):
    practice_page._driver.execute_script("""
        const input = document.createElement('input');
        input.id = 'readonly-contract';
        input.value = 'old';
        input.readOnly = true;
        document.body.appendChild(input);
        setTimeout(() => { input.readOnly = false; }, 400);
    """)
    try:
        locator = practice_page.locator("#readonly-contract")
        locator.fill("ready")
        assert locator.get_attribute("value") == "ready"
    finally:
        practice_page._driver.execute_script("document.getElementById('readonly-contract')?.remove();")
