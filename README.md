# Pylenium Framework

A Python UI Automation framework built from scratch, inspired by the simplicity and design of **Playwright**.

## Features (Phase 2 - Foundation)

- **Layered Configuration**: Priority-based config loading (CLI > Env Vars > YAML > Defaults).
- **Builder Pattern**: Fluent configuration for `BrowserOptions` (headless, window size).
- **Factory Pattern**: Centralized `WebDriver` initialization (`BrowserFactory`).
- **Facade Pattern**: Simplified `Page` object wrapping Selenium's complex APIs.

## Project Structure

```text
Sele3-Aug2026/
├── poetry.lock             # Dependency lockfile
├── pyproject.toml          # Poetry configuration
├── config/                 # User environment configs (staging, prod)
├── data/                   # Test data (JSON, CSV)
├── pages/                  # Page Object Model (POM) classes
├── pylenium/               # Framework Core
│   ├── config/             # Config Singleton & default yaml
│   └── core/               # Browser, Page, Factory, Options
├── tests/                  # User tests
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

Currently in Phase 2, a sanity test is provided to verify foundation components:

```bash
poetry run python tests/test_foundation.py
```

## Configuration

The framework uses a Singleton `Config` class. You can override default settings via Environment Variables:

- `PYLENIUM_BROWSER=firefox`
- `PYLENIUM_HEADLESS=true`
- `PYLENIUM_BASE_URL=https://example.com`
