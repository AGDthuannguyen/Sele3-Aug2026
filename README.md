# Pylenium Framework

A Python UI Automation framework built from scratch, inspired by the simplicity and design of **Playwright**.

## Features

### Layered Configuration
Configuration is managed through a priority-based system (CLI > Env Vars > YAML > Defaults) powered by **Dynaconf**.
- Override default settings via Environment Variables:
  - `PYLENIUM_BROWSER__TYPE=firefox`
  - `PYLENIUM_BROWSER__HEADLESS=true`
  - `PYLENIUM_BROWSER__BASE_URL=https://example.com`

### Smart Locators & Auto-Wait
Locators in Pylenium are **lazy** and **auto-wait** by default. They do not query the DOM until an action is performed, reducing the risk of `StaleElementReferenceException` by re-evaluating the DOM on retries.

**Setup Example:**
```python
from pylenium import Browser

# Launch a session and wrap its current window
browser = Browser.launch(headless=True)
try:
    page = browser.new_page()
    page.goto("https://example.com")
finally:
    browser.close()
```

**Examples:**
```python
# Create locators using Page (auto-detects CSS vs XPath)
username = page.locator("#username")
button = page.get_by_role("button", name="Submit")
link = page.get_by_text("Click me")

# Perform actions (automatically waits for elements to be ready)
username.fill("testuser")  # Waits for visible, clears, then types
button.click()             # Waits for clickable, then clicks
text = link.text()         # Waits for visible, then returns text
```

**Replacing text vs sending keys:**
```python
from selenium.webdriver.common.keys import Keys

username.fill("alice")               # Clear and replace existing content
username.send_keys(Keys.END, "123")  # Move to the end explicitly and type more
```

`send_keys(*values)` resolves, checks visible/enabled state and sends within one
wait. Stale during the command now retries against a fresh element, using the
same timeout budget. It does not clear or reposition the cursor. Each retry
resends all values, so partial input or keyboard effects may repeat. Other command
errors propagate. This replaces the earlier send-once policy and is not an upload helper.

`click()` uses a native Selenium click. If intercepted, it scrolls the target to
the viewport center, then resolves again on the next poll under the original
timeout. Scroll does not remove persistent overlays; these eventually time out.
No JavaScript click is used to bypass browser interaction checks.

`fill(text)` retries clear and typing together, clearing again before each retry.
An empty string only clears the element. Unsupported targets raise `ValueError`;
hidden, disabled or readonly editable controls wait until ready.

**Immediate state queries (behavior change):** `is_visible()` and `is_enabled()`
read once without waiting. Missing and stale elements now raise their Selenium
exceptions; stale is no longer converted to `False`. A valid hidden or disabled
element still returns `False`. Use `expect()` when retrying assertions are needed;
stale retries in both positive and negative assertions, and only negative
visibility accepts a missing element.

**Child Scope & Collections:**
You can chain locators to search within a parent element, or interact with multiple elements.
```python
container = page.locator("#container")

# Child scope: search within #container
first_item = container.locator(".item").first()

# Collections
second_item = container.locator(".item").nth(1)
all_items = container.locator(".item").all()
count = container.locator(".item").count()
```

### Smart Assertions (`expect`)
Pylenium provides an `expect()` function for assertions with **auto-retry** mechanisms. Instead of failing immediately, assertions will poll the DOM until the condition is met or the timeout is reached.

**Examples:**
```python
from pylenium import expect

# Locator assertions
expect(username).to_be_visible()
expect(username).to_have_attribute("type", "text")
expect(username).to_have_text("Welcome")

# Negation (asserting the opposite)
expect(hidden_element).not_.to_be_visible()

# Page assertions
expect(page).to_have_title("My Page")
expect(page).to_have_url("dashboard")
```

### Soft Assertions

Use `soft_assertions()` to collect assertion failures and report them together at
the end of a block. Each `soft.check()` runs a normal `expect()` assertion with
its own timeout. `expect()` outside this block remains a hard assertion.

```python
from pylenium import expect, soft_assertions

with soft_assertions() as soft:
    soft.check(expect(username).to_be_visible)
    soft.check(expect(page).to_have_title, "Dashboard")
    soft.check(expect(error_message).not_.to_be_visible)
```

Only failures raised inside `soft.check()` are collected; unexpected WebDriver
errors still stop the test immediately.

## Project Structure
```text
Sele3-Aug2026/
├── poetry.lock             # Dependency lockfile
├── pyproject.toml          # Poetry configuration
├── config/                 # User environment configs
├── data/                   # Test data (JSON, CSV)
├── pages/                  # Automation Exercise page objects (LoginPage)
├── pylenium/               # Framework Core
│   ├── assertions/         # Smart assertions (expect)
│   ├── config/             # Dynaconf settings
│   ├── core/               # Browser, Page, Locator, Strategies
│   ├── plugins/            # pytest browser/page fixtures and CLI options
│   ├── utils/              # JSON and CSV test-data reader
│   └── waits/              # AutoWait backed by Selenium WebDriverWait
├── tests/                  # Core unit tests and public-site browser tests
└── .gitignore
```

## Getting Started

### Prerequisites
- **Python 3.12+**
- **Poetry** (Package Manager)

### Installation
Clone the repository and install dependencies using Poetry:
```bash
poetry install
```

### Running Tests
The framework comes with a suite of tests to verify its core functionality (Browser, Locators, Assertions):
```bash
poetry run pytest tests/ --headless -v
```

Automation Exercise (https://www.automationexercise.com/) is the public browser
test target. Browser tests require network access and a working site; an outage
is reported as a failure, not silently skipped.

```bash
poetry run pytest -m "not browser" -q  # Core and plugin tests, no website needed
poetry run pytest -m browser --headless -q  # Live website integration tests
```

`tests/test_locator.py` and `tests/test_assertions.py` retain useful core regression
tests from phase 3. Browser scenarios use the `browser` marker in
`tests/test_browser_integration.py` and `tests/test_locator.py`; obsolete
local HTML tests have been replaced. A few browser edge cases inject temporary
elements into the current page to test quoting, readonly and contenteditable.

Tests serve acceptance of the current phase, not a permanent suite requirement.
Later phases may replace or remove checks that no longer serve their scope.
BasePage unit checks reuse Automation Exercise's LoginPage and URLs with a mock
driver; they do not contact another website.

## Phase 4: Page Objects and pytest

After `poetry install`, pytest discovers the Pylenium plugin automatically through
its `pytest11` entry point. No manual plugin registration is needed. Tests that
request neither `browser` nor `page` do not launch a browser.

```python
from pages.login_page import LoginPage
from pylenium import expect


def test_login_form(practice_page):
    LoginPage(practice_page).wait_until_loaded(timeout=5)
    expect(practice_page.locator("[data-qa='login-email']")).to_be_visible()
```

Run against Automation Exercise, or pass `--base-url` for a compatible deployment:

```bash
poetry run pytest -m browser --browser=chrome --headless --base-url=https://www.automationexercise.com/
```

- `browser` and `page` are function-scoped. Each requesting test gets a new
  WebDriver session, closed in browser teardown even if page setup or the test fails.
- `Browser.new_page()` wraps the current window; it creates neither a tab nor a
  new session. The browser fixture owns cleanup. Tests normally should not call
  `page.close()` or `browser.close()` themselves.
- CLI values override configuration without mutating global settings. Omitting
  `--browser`, `--headless`/`--headed`, or `--base-url` retains configured values.
  The two display flags cannot be combined.
- Relative navigation uses `urljoin`: with base `https://host/app/`, `child`
  becomes `/app/child`, while `/child` starts at the host root. Absolute URLs,
  including local `file:` URLs, remain unchanged. This corrects the previous
  string-concatenation behavior for leading slashes.
- `is_loaded()` must be an immediate boolean check. Do not call waiting locator
  actions or assertions inside it. `wait_until_loaded(timeout=...)` owns one
  readiness wait. `open()` only navigates using WebDriver's page-load timeout;
  it does not silently add a readiness wait. Chain the two explicitly when needed.
- `tests/conftest.py` defines `practice_page`: it uses the plugin's browser fixture,
  applies the site's base URL and opens `/login`. The plugin's generic `page`
  fixture remains unchanged for other applications. pytest discovers conftest
  automatically; tests do not import it.
- The multiline strings in `test_pytest_plugin.py` are executable subprocess
  test modules created by pytester, not commented-out code. These checks exercise
  real fixture teardown while mocking browser creation.

Browser creation is cleaned up if post-launch configuration fails. A cleanup
failure is chained to the original setup exception.

## Batch 1: Failure reporting and GitHub Actions

The pytest plugin captures one PNG when setup or the test body fails and its
browser fixture has a session. Capture happens before browser teardown, including
when a dependent page fixture fails. It never launches a browser for reporting.
Tests that close their session early may have no screenshot. Teardown failures
do not trigger screenshots because the session may already be closed.

Screenshots are saved under `artifacts/screenshots` (override with
`--screenshots-dir`) and attached through `allure-pytest` when that plugin is
installed. Capture or attachment errors are diagnostic messages; they do not
replace the test failure or prevent cleanup. Set
`PYLENIUM_REPORTING__SCREENSHOT_ON_FAILURE=false` to disable capture.

```bash
poetry run pytest --headless --junitxml=artifacts/junit.xml --alluredir=artifacts/allure-results
```

Allure results are raw data, not an HTML report. With the Allure command-line tool
installed separately, run `allure serve artifacts/allure-results` to view them.
Use a fresh results directory for each run to avoid mixing old and new results.

`.github/workflows/verify.yml` runs on branch pushes, pull requests targeting
`main`, and manual dispatch. It installs the locked dependencies on Python 3.12
and runs two independent jobs: unit/plugin tests on Linux and browser integration
tests on Windows
(Chrome, Firefox, and Edge headless on pushes and PRs). Both jobs upload
available JUnit, Allure, and screenshot artifacts even if tests fail; artifacts
are retained for 14 days.
New runs cancel superseded runs for the same event/ref.
The browser job opens the public Automation Exercise site. A failure of that
site remains a CI failure with the available screenshot and test results. For
manual runs, GitHub Actions inputs can override the browser strategy name,
headless mode, base URL, navigation timeout, and failure limit. Push and pull
request runs use headless mode; a manual headed run uses `xvfb-run` on the Linux
runner. Browser names are resolved from the strategy registry when the fixture
launches; a consumer can register a new strategy before test setup.

Browser tests require the selected browser and access to the public practice
site. Navigation timeouts fail CI; the workflow does not skip failures or retry
the suite to hide them. CI allows 60 seconds for navigation through
`PYLENIUM_BROWSER__PAGE_LOAD_TIMEOUT`; action and assertion timeouts remain
unchanged. For a comparable local run in PowerShell:

```powershell
$env:PYLENIUM_BROWSER__PAGE_LOAD_TIMEOUT = "60"
poetry run pytest -m browser --headless --maxfail=1
```

Failure reporting and fixture cleanup temporarily bound WebDriver HTTP reads
to 10 seconds, restoring the original transport setting afterward. HTTP retries
can extend that duration; CI also bounds the entire test step to 10 minutes.
Inspect the failed step and downloaded artifacts from the Actions run.
Jenkins, parallel execution, and package publishing are planned for later work.

## Batch 2: Cross-browser runs and test data

The same `browser` tests run on Chrome, Firefox, and Edge in CI. A manual workflow
dispatch runs only the browser named by its `browser` input. Locally, select one
with `--browser=firefox` or `--browser=edge`. Safari is available through
`--browser=safari` on macOS after enabling Safari's remote automation, but it
does not support headless mode; use `--headed`. Safari is not included in the
default CI run. To exercise Safari through a manual workflow dispatch,
choose `browser=safari` and `headless=false`; that run uses a macOS runner.

`DataReader` loads UTF-8 JSON or CSV files using Python's standard library. It
returns parsed JSON values or CSV rows as dictionaries, and leaves file and
parse errors unchanged:

```python
from pathlib import Path

from pylenium import DataReader

cases = DataReader.read_json(
    Path(__file__).resolve().parents[1] / "data" / "invalid_login_cases.json"
)
rows = DataReader.read_csv("data/users.csv")
```

CSV files need a header row; values are strings. The parameterized login test in
`tests/test_browser_integration.py` shows how to pass JSON cases to pytest.
