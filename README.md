# Pylenium

Pylenium is a small Selenium framework for Python. It provides lazy locators, automatic
waits for actions, retrying assertions, and pytest fixtures. It uses Selenium WebDriver for
browser control.

## Requirements

- Python 3.12, 3.13, or 3.14
- Poetry
- An installed browser for browser tests
- Network access for the repository's live tests against [Automation Exercise](https://www.automationexercise.com/)

## Install

From the repository root:

```bash
poetry install
```

## First browser session

```python
from pylenium import Browser, expect

browser = Browser.launch(headless=True)
try:
    page = browser.new_page(base_url="https://www.automationexercise.com/")
    page.goto("/login")
    expect(page.locator("[data-qa='login-email']")).to_be_visible()
finally:
    browser.close()
```

`Browser.new_page()` wraps the current window. It does not open a new tab or create an
isolated session. `browser.close()` quits the session. In pytest, use the fixtures below
instead of closing the browser yourself.

## Locators and actions

```python
from selenium.webdriver.common.keys import Keys

email = page.locator("[data-qa='login-email']")
password = page.locator("[data-qa='login-password']")

email.fill("user@example.com")       # Clear, then type
email.send_keys(Keys.END, ".test")   # Type without clearing
password.fill("secret")
page.locator("[data-qa='login-button']").click()

value = email.get_attribute("value")
text = page.get_by_text("Login to your account").text()
```

`locator()` accepts CSS or XPath selectors. A selector starting with `/`, `./`, or `(` is
treated as XPath; other selectors use CSS. A child locator searches within its parent:

```python
items = page.locator(".list").locator(".item")
first = items.first()
second = items.nth(1)
count = items.count()
all_items = items.all()
```

Locators are lazy. Actions such as `click()`, `fill()`, `send_keys()`, `text()`, and
`get_attribute()` resolve the element and retry transient failures within one timeout
budget. An intercepted click scrolls the element into view before retrying. A `send_keys()`
retry can repeat partial input. `count()` reads current matches without waiting; `all()`
uses that count to return lazy indexed locators. `is_visible()` and `is_enabled()` read once
without waiting. Missing or stale elements can raise Selenium exceptions.

`get_by_role(role, name=...)` matches an explicit `role` attribute, optionally using
`aria-label` or direct text for the name. It does not calculate the browser's accessible
role. `get_by_text(text)` matches normalized direct text exactly. For other matching rules,
use `locator()`.

## Assertions

`expect()` retries until its condition passes or its timeout expires. Text, title, and URL
assertions use substring matching.

```python
from pylenium import expect

expect(email).to_be_visible()
expect(email).to_be_enabled()
expect(email).to_have_attribute("type", "email")
expect(page).to_have_url("/login")
expect(page.locator("#missing")).not_.to_be_visible()
```

`not_.to_be_visible()` passes when the element is absent. Other negative element assertions
require an existing element. Pass `timeout=` to `expect()` to override the configured
assertion timeout.

Use `soft_assertions()` when several assertions should run before reporting their failures
together:

```python
from pylenium import expect, soft_assertions

with soft_assertions() as soft:
    soft.check(expect(email).to_be_visible)
    soft.check(expect(page).to_have_url, "/login")
```

Each check keeps its own retry timeout. `SoftAssertionError.failures` contains the original
`AssertionError` objects. Unexpected WebDriver errors still stop the test immediately.

## Page objects and test data

Subclass `BasePage` to group locators and actions. Implement `is_loaded()` as a single
immediate check; `wait_until_loaded()` performs the retry. `open()` navigates but does not
wait for application readiness.

The repository's [LoginPage](pages/login_page.py) is an example:

```python
from pages.login_page import LoginPage

login = LoginPage(page).open().wait_until_loaded(timeout=5)
```

Mark reusable page-object operations once, rather than adding report code to
every test:

```python
from pylenium import step

@step("Submit login form")
def login(self, email: str, password: str) -> None:
    self._email.fill(email)
    self._password.fill(password)
    self._submit.click()
```

No Allure import is needed in the page object. `open()`, `wait_until_loaded()`,
locator actions, and `expect()` assertions also produce steps. Internal readiness
polls do not. The decorator does not include method arguments such as passwords
in step names.

`DataReader.read_json(path)` and `DataReader.read_csv(path)` load UTF-8 test data. For
example, `DataReader.read_json("data/invalid_login_cases.json")` reads the cases used by the
repository tests. CSV input needs a header row and returns dictionaries of strings.

## Run tests

After installation, Pylenium's pytest plugin provides function-scoped `browser` and `page`
fixtures. Each test requesting a browser gets its own WebDriver session, which the fixture
closes. Tests without these fixtures do not launch a browser.

```python
import pytest

from pylenium import expect


@pytest.mark.browser
def test_login_page(page):
    page.goto("https://www.automationexercise.com/login")
    expect(page.locator("[data-qa='login-email']")).to_be_visible()
```

Run from the repository root:

```bash
poetry run pytest -m "not browser" -q
poetry run pytest -m browser --browser=chrome --headless -q
poetry run pytest -m browser --browser=chrome --headless -n 2 -q
```

The `browser` tests visit a public website and fail if that site or the network is
unavailable. `-n 2` uses two pytest-xdist workers and separate browser sessions.

The plugin accepts `--browser`, `--headless` or `--headed`, `--base-url`,
`--reports-root`, `--screenshots-dir`, `--page-load-timeout`, `--action-timeout`, and
`--assertion-timeout`. The two display flags cannot be combined. Timeouts are
finite, non-negative seconds; zero makes action and assertion checks immediate.
The repository's `practice_page` fixture in [tests/conftest.py](tests/conftest.py) opens Automation
Exercise; it is an example fixture, not part of the framework API.

## Configuration and browser support

Defaults are in [default_config.yaml](pylenium/config/default_config.yaml). Dynaconf
also reads environment variables with the `PYLENIUM_` prefix and double underscores
for nested keys:

| Setting | Default | Environment variable |
| --- | --- | --- |
| Browser | Chrome | `PYLENIUM_BROWSER__TYPE` |
| Headless | false | `PYLENIUM_BROWSER__HEADLESS` |
| Page-load timeout | 30 seconds | `PYLENIUM_BROWSER__PAGE_LOAD_TIMEOUT` |
| Action timeout | 10 seconds | `PYLENIUM_WAITS__TIMEOUT` |
| Assertion timeout | 5 seconds | `PYLENIUM_ASSERTIONS__TIMEOUT` |
| Failure screenshot | true | `PYLENIUM_REPORTING__SCREENSHOT_ON_FAILURE` |

The corresponding pytest CLI options override browser type, headless mode, and the three
timeouts. `--base-url` overrides the URL passed to the `page` fixture. Explicit API
timeout arguments take priority over CLI settings, which take priority over environment
variables and defaults. Polling intervals and screenshot behavior use environment variables
or Dynaconf configuration; there is no general CLI override for every setting.

Chrome, Firefox, and Edge are available with `--browser=chrome`, `--browser=firefox`, or
`--browser=edge`. Safari is available on macOS with remote automation enabled and must run
headed. Safari is not part of the default CI run.

To add a driver, register a `BrowserStrategy` subclass before a browser fixture starts. For
example, put this in a consumer project's `conftest.py`:

```python
from selenium import webdriver
from pylenium.core.browser_strategy import BROWSER_STRATEGIES, ChromeStrategy


class RemoteChrome(ChromeStrategy):
    def create_driver(self, options):
        return webdriver.Remote(
            command_executor="http://localhost:4444",
            options=options,
        )

BROWSER_STRATEGIES["remote_chrome"] = RemoteChrome
```

Then run with `--browser=remote_chrome`. Browser strategies are extensible; custom Locator
and reporter registries are not currently provided.

## Results and CI

Each pytest invocation writes into its own `artifacts/runs/<run-id>/` directory.
After it finishes, the plugin copies that run into `artifacts/latest/` for easy
access; starting another run does not delete an active run's evidence. The report
contains `junit.xml`, neutral step records in `steps/`, and `allure-results/`
when Allure pytest is installed. Failure screenshots go to `screenshots/` and
are attached to Allure. Screenshot failures do not replace the test failure.
For a quick local demonstration in PowerShell or Command Prompt:

```powershell
poetry run pytest tests\test_browser_integration.py::test_login_form_locators_and_assertions tests\test_browser_integration.py::test_page_object_opens_login_form tests\test_browser_integration.py::test_login_rejects_unknown_account --browser chrome --headed
allure serve artifacts/latest/allure-results
```

To inspect a failure, temporarily change the login email selector in
`test_login_form_locators_and_assertions` to a missing selector, rerun the pytest
command, and open Allure again. Restore the selector afterward.

Allure output is raw result data. With the separate Allure command-line tool,
run `allure serve artifacts/latest/allure-results` to view it. Explicit
`--junitxml`, `--alluredir`, and `--screenshots-dir` paths still override the
automatic locations. A JUnit testcase includes a plain-text step summary;
Allure displays the nested steps and failure screenshot.

[GitHub Actions](.github/workflows/verify.yml) runs unit tests and Chrome, Firefox,
and Edge browser tests on pushes and pull requests. Manual runs can choose the browser,
headless mode, base URL, page-load, action and assertion timeouts, and failure limit.
Safari requires a manual headed run on macOS. Results and available screenshots are uploaded as artifacts.

[Jenkinsfile](Jenkinsfile) runs unit and browser tests with two workers on a Windows
agent. It accepts browser, base URL, and page-load, action and assertion timeout parameters.
A real Jenkins run requires a configured Windows agent and installed browser.

See the [class relationships](diagram/relationships_map.md) and
[test lifecycle](diagram/lifecycle.md) diagrams for the current architecture.
