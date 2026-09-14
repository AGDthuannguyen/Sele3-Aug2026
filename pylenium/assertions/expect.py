"""Smart assertions with auto-retry, inspired by Playwright's expect()."""

from __future__ import annotations
from pylenium.constants.timeouts import Timeout


def _retry_until(driver, timeout: float, polling: float, condition_fn, msg: str, is_negated: bool):
    """Shared retry helper using Selenium WebDriverWait.

    Args:
        driver: Selenium WebDriver instance.
        timeout: Max seconds to wait.
        polling: Polling interval.
        condition_fn: Callable returning bool.
        msg: Assertion message.
        is_negated: Whether the assertion is negated.
    """
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException

    wait = WebDriverWait(
        driver, 
        timeout, 
        polling, 
        ignored_exceptions=(StaleElementReferenceException, NoSuchElementException)
    )
    try:
        wait.until(lambda _: condition_fn() != is_negated)
    except TimeoutException:
        negated_msg = " NOT" if is_negated else ""
        raise AssertionError(f"Assertion failed after {timeout}s:{negated_msg} {msg}")


from typing import TYPE_CHECKING

from pylenium.config.config import settings

if TYPE_CHECKING:
    from pylenium.core.locator import Locator
    from pylenium.core.page import Page


class LocatorAssertions:
    """Auto-retry assertions for Locator elements."""

    def __init__(self, locator: Locator, timeout: float | None = None,
                 is_negated: bool = False):
        self._locator = locator
        self._timeout = timeout or Timeout.ASSERTION.value
        self._polling = settings.get("assertions.polling_interval", 0.25)
        self._is_negated = is_negated

    @property
    def not_(self) -> "LocatorAssertions":
        """Return a negated copy of this assertion.

        Example:
            expect(locator).not_.to_be_visible()
        """
        return LocatorAssertions(
            self._locator, self._timeout, is_negated=not self._is_negated
        )

    def _run(self, condition_fn, msg: str):
        driver = getattr(self._locator, "_resolve_driver", lambda: None)()
        if not driver:
            raise ValueError("WebDriver not available for assertion retry")
        _retry_until(driver, self._timeout, self._polling, condition_fn, msg, self._is_negated)

    def to_have_text(self, expected: str) -> None:
        """Assert that the element's text content matches the expected string."""
        def condition():
            return expected in self._locator.text()
        self._run(condition, f"Expected element to have text '{expected}'")

    def to_be_visible(self) -> None:
        """Assert that the element is visible on the page."""
        def condition():
            return self._locator.is_visible()
        self._run(condition, "Expected element to be visible")

    def to_be_enabled(self) -> None:
        """Assert that the element is enabled."""
        def condition():
            return self._locator.is_enabled()
        self._run(condition, "Expected element to be enabled")

    def to_have_attribute(self, name: str, value: str) -> None:
        """Assert that the element has the specified attribute with the expected value."""
        def condition():
            return self._locator.get_attribute(name) == value
        self._run(condition, f"Expected element to have attribute '{name}' = '{value}'")


class PageAssertions:
    """Auto-retry assertions for Page objects."""

    def __init__(self, page: Page, timeout: float | None = None,
                 is_negated: bool = False):
        self._page = page
        self._timeout = timeout or Timeout.ASSERTION.value
        self._polling = settings.get("assertions.polling_interval", 0.25)
        self._is_negated = is_negated

    @property
    def not_(self) -> "PageAssertions":
        """Return a negated copy of this assertion."""
        return PageAssertions(
            self._page, self._timeout, is_negated=not self._is_negated
        )

    def _run(self, condition_fn, msg: str):
        driver = getattr(self._page, "_driver", None) or getattr(self._page, "driver", None)
        if not driver:
            raise ValueError("WebDriver not available for assertion retry")
        _retry_until(driver, self._timeout, self._polling, condition_fn, msg, self._is_negated)

    def to_have_url(self, expected: str) -> None:
        """Assert that the page URL contains the expected string."""
        def condition():
            return expected in self._page.url()
        self._run(condition, f"Expected page URL to contain '{expected}'")

    def to_have_title(self, expected: str) -> None:
        """Assert that the page title contains the expected string."""
        def condition():
            return expected in self._page.title()
        self._run(condition, f"Expected page title to contain '{expected}'")


def expect(target: Locator | Page) -> LocatorAssertions | PageAssertions:
    """Create an assertion object for the given target.

    This is the main entry point for smart assertions.

    Args:
        target: A Locator or Page instance.

    Returns:
        LocatorAssertions or PageAssertions depending on the target type.

    Raises:
        TypeError: If the target is not a Locator or Page.
    """
    # Import here to avoid circular imports at module level
    from pylenium.core.locator import Locator
    from pylenium.core.page import Page

    if isinstance(target, Locator):
        return LocatorAssertions(target)
    elif isinstance(target, Page):
        return PageAssertions(target)
    else:
        raise TypeError(
            f"expect() requires a Locator or Page, got {type(target).__name__}"
        )
