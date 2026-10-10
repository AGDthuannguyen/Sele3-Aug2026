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

The plugin accepts `--browser`, `--headless` or `--headed`, `--base-url`, and
`--screenshots-dir`. The two display flags cannot be combined. The repository's
`practice_page` fixture in [tests/conftest.py](tests/conftest.py) opens Automation
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

The corresponding pytest CLI options override browser type and headless mode. `--base-url`
overrides the URL passed to the `page` fixture. Other settings in the table use environment
variables or Dynaconf configuration; there is no general CLI override for every setting.

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

On a failed test with a live browser, the pytest plugin saves a screenshot in
`artifacts/screenshots` and attaches it to Allure when the Allure pytest plugin is
installed. Screenshot errors do not replace the test failure. pytest can also produce JUnit
and Allure results:

```bash
poetry run pytest --headless --junitxml=artifacts/junit.xml --alluredir=artifacts/allure-results
```

Allure output is raw result data; viewing it requires the Allure command-line tool.

[GitHub Actions](.github/workflows/verify.yml) runs unit tests and Chrome, Firefox,
and Edge browser tests on pushes and pull requests. Manual runs can choose the browser,
headless mode, base URL, page-load timeout, and failure limit. Safari requires a manual
headed run on macOS. Results and available screenshots are uploaded as artifacts.

[Jenkinsfile](Jenkinsfile) runs unit and browser tests with two workers on a Windows
agent. It accepts browser, base URL, and page-load timeout parameters. A real Jenkins
run requires a configured Windows agent and installed browser.

See the [class relationships](diagram/relationships_map.md) and
[test lifecycle](diagram/lifecycle.md) diagrams for the current architecture.
