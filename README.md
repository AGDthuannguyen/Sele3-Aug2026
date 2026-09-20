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
Locators in Pylenium are **lazy** and **auto-wait** by default. They do not query the DOM until an action is performed, preventing `StaleElementReferenceException`.

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
expect(hidden_element).not_().to_be_visible()

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
│   └── waits/              # AutoWait and Conditions
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
