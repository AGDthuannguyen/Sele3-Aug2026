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

# Launch session and get the new page
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

## Project Structure
```text
Sele3-Aug2026/
├── poetry.lock             # Dependency lockfile
├── pyproject.toml          # Poetry configuration
├── config/                 # User environment configs
├── data/                   # Test data (JSON, CSV)
├── pages/                  # Page Object Model (POM) classes
├── pylenium/               # Framework Core
│   ├── assertions/         # Smart assertions (expect)
│   ├── config/             # Dynaconf settings
│   ├── core/               # Browser, Page, Locator, Strategies
│   └── waits/              # AutoWait backed by Selenium WebDriverWait
├── tests/                  # User tests
│   └── html/               # Local test resources
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
poetry run pytest tests/ -v
```

The new send_keys browser check uses https://the-internet.herokuapp.com/login
and requires network access. Existing phase 3 local fixtures remain unchanged;
phase 4's fixture/plugin infrastructure is not required.
