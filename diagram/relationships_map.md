# Implemented relationships

```mermaid
classDiagram
    direction LR

    class Browser {
        -WebDriver _driver
        +launch(browser_type, headless)$ Browser
        +new_page(base_url) Page
        +close()
    }
    class BrowserFactory {
        +create(browser_type, options)$ WebDriver
    }
    class BrowserOptions {
        +headless(enabled) BrowserOptions
        +window_size(width, height) BrowserOptions
        +add_argument(arg) BrowserOptions
        +build()
    }
    class BrowserStrategy {
        <<abstract>>
        +create_options()
        +create_driver(options) WebDriver
        +apply_headless(options)
    }
    class ChromeStrategy
    class FirefoxStrategy
    class EdgeStrategy
    class SafariStrategy
    class Page {
        +goto(url)
        +locator(selector) Locator
        +get_by_role(role, name) Locator
        +get_by_text(text) Locator
        +screenshot(path) bytes
        +close()
    }
    class Locator {
        +click()
        +send_keys(values)
        +fill(text)
        +text() str
        +get_attribute(name)
        +is_visible() bool
        +is_enabled() bool
        +locator(selector) Locator
        +first() Locator
        +nth(index) Locator
        +all() list
        +count() int
    }
    class BasePage {
        <<abstract>>
        +open() BasePage
        +is_loaded() bool
        +wait_until_loaded(timeout) BasePage
    }
    class AutoWait {
        +until(condition_fn, msg) Any
    }
    class LocatorAssertions {
        +not_ LocatorAssertions
        +to_be_visible()
        +to_be_enabled()
        +to_have_text(expected)
        +to_have_attribute(name, value)
    }
    class PageAssertions {
        +not_ PageAssertions
        +to_have_url(expected)
        +to_have_title(expected)
    }
    class DataReader {
        +read_json(path)$
        +read_csv(path)$ list
    }

    BrowserStrategy <|-- ChromeStrategy
    BrowserStrategy <|-- FirefoxStrategy
    BrowserStrategy <|-- EdgeStrategy
    BrowserStrategy <|-- SafariStrategy
    Browser --> BrowserFactory : creates driver through
    Browser --> BrowserOptions : configures
    BrowserFactory --> BrowserOptions : builds
    BrowserOptions --> BrowserStrategy : selects from registry
    Browser --> Page : wraps current window
    Page --> Locator : creates lazy locator
    Locator --> Locator : scopes child locator
    Locator --> AutoWait : retries actions
    BasePage --> Page : navigates and checks
    BasePage --> AutoWait : waits for readiness
    LocatorAssertions --> Locator : reads
    LocatorAssertions --> AutoWait : retries checks
    PageAssertions --> Page : reads
    PageAssertions --> AutoWait : retries checks
```

The pytest plugin is a module, not a class. It owns function-scoped browser/page
fixtures and captures failure screenshots. pytest-xdist runs these fixtures in
separate worker processes; GitHub Actions and Jenkins invoke pytest and collect
JUnit, Allure, and screenshot artifacts. `DataReader` is independent of the
browser and assertion classes.
