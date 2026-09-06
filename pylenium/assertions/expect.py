"""Smart assertions with auto-retry, inspired by Playwright's expect()."""

from __future__ import annotations

import time
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
        self._timeout = timeout or settings.get("assertions.timeout", 5)
        self._polling = settings.get("assertions.polling_interval", 0.25)
        self._is_negated = is_negated

    def not_(self) -> LocatorAssertions:
        """Return a negated copy of this assertion.

        Example:
            expect(locator).not_().to_be_visible()
        """
        return LocatorAssertions(
            self._locator, self._timeout, is_negated=not self._is_negated
        )

    def to_have_text(self, expected: str) -> None:
        """Assert that the element's text content matches the expected string.

        Args:
            expected: The expected text content.
        """
        def condition():
            actual = self._locator.text()
            return expected in actual

        self._retry_until(
            condition,
            f"Expected element to have text '{expected}'"
        )

    def to_be_visible(self) -> None:
        """Assert that the element is visible on the page."""
        def condition():
            return self._locator.is_visible()

        self._retry_until(condition, "Expected element to be visible")

    def to_be_enabled(self) -> None:
        """Assert that the element is enabled."""
        def condition():
            return self._locator.is_enabled()

        self._retry_until(condition, "Expected element to be enabled")

    def to_have_attribute(self, name: str, value: str) -> None:
        """Assert that the element has the specified attribute with the expected value.

        Args:
            name: The attribute name.
            value: The expected attribute value.
        """
        def condition():
            actual = self._locator.get_attribute(name)
            return actual == value

        self._retry_until(
            condition,
            f"Expected element to have attribute '{name}' = '{value}'"
        )

    def _retry_until(self, condition_fn, msg: str) -> None:
        """Retry a condition function until it passes or timeout is reached.

        The condition is retried at regular polling intervals. If negated,
        the condition result is inverted.

        Args:
            condition_fn: A callable returning True/False.
            msg: Description of the assertion for error messages.

        Raises:
            AssertionError: If the condition is not met within the timeout.
        """
        end_time = time.time() + self._timeout
        last_error = None

        while time.time() < end_time:
            try:
                result = condition_fn()
                if self._is_negated:
                    result = not result
                if result:
                    return
            except Exception as e:
                last_error = e
                if self._is_negated:
                    # For negated assertions, exceptions mean element not found
                    # which is a passing condition for not_().to_be_visible() etc.
                    return
            time.sleep(self._polling)

        negated_msg = " NOT" if self._is_negated else ""
        error_detail = f" (last error: {last_error})" if last_error else ""
        raise AssertionError(
            f"Assertion failed after {self._timeout}s:{negated_msg} {msg}{error_detail}"
        )


class PageAssertions:
    """Auto-retry assertions for Page objects."""

    def __init__(self, page: Page, timeout: float | None = None,
                 is_negated: bool = False):
        self._page = page
        self._timeout = timeout or settings.get("assertions.timeout", 5)
        self._polling = settings.get("assertions.polling_interval", 0.25)
        self._is_negated = is_negated

    def not_(self) -> PageAssertions:
        """Return a negated copy of this assertion."""
        return PageAssertions(
            self._page, self._timeout, is_negated=not self._is_negated
        )

    def to_have_url(self, expected: str) -> None:
        """Assert that the page URL contains the expected string.

        Args:
            expected: The expected URL or substring.
        """
        def condition():
            actual = self._page.url()
            return expected in actual

        self._retry_until(
            condition,
            f"Expected page URL to contain '{expected}'"
        )

    def to_have_title(self, expected: str) -> None:
        """Assert that the page title contains the expected string.

        Args:
            expected: The expected title or substring.
        """
        def condition():
            actual = self._page.title()
            return expected in actual

        self._retry_until(
            condition,
            f"Expected page title to contain '{expected}'"
        )

    def _retry_until(self, condition_fn, msg: str) -> None:
        """Retry a condition function until it passes or timeout is reached.

        Args:
            condition_fn: A callable returning True/False.
            msg: Description of the assertion for error messages.

        Raises:
            AssertionError: If the condition is not met within the timeout.
        """
        end_time = time.time() + self._timeout
        last_error = None

        while time.time() < end_time:
            try:
                result = condition_fn()
                if self._is_negated:
                    result = not result
                if result:
                    return
            except Exception as e:
                last_error = e
                if self._is_negated:
                    return
            time.sleep(self._polling)

        negated_msg = " NOT" if self._is_negated else ""
        error_detail = f" (last error: {last_error})" if last_error else ""
        raise AssertionError(
            f"Assertion failed after {self._timeout}s:{negated_msg} {msg}{error_detail}"
        )


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
