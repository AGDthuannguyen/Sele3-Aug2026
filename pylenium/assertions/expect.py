"""Smart assertions with auto-retry, inspired by Playwright's expect().

Uses :class:`~pylenium.waits.auto_wait.AutoWait` for retry/polling so that
timeout, polling interval, and ignored-exception lists are defined in one
place instead of being duplicated here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pylenium.config.config import settings
from pylenium.constants.timeouts import Timeout

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

    # -- private helpers -------------------------------------------------- #

    def _run(self, condition_fn, msg: str) -> None:
        """Retry *condition_fn* until it agrees with the negation flag.

        Delegates to :class:`AutoWait` so that timeout, polling, and the
        ignored-exception list are defined in a single place.
        """
        from pylenium.waits.auto_wait import AutoWait
        from selenium.common.exceptions import TimeoutException

        driver = self._locator._resolve_driver()
        auto_wait = AutoWait(driver, timeout=self._timeout, polling=self._polling)

        try:
            auto_wait.until(
                lambda _: condition_fn() != self._is_negated,
                msg=msg,
            )
        except TimeoutException:
            negated_msg = " NOT" if self._is_negated else ""
            raise AssertionError(
                f"Assertion failed after {self._timeout}s:{negated_msg} {msg}"
            )

    def _evaluate(self, eval_fn) -> bool:
        """Safely query the immediate DOM state via *eval_fn*.

        Calls ``eval_fn(element)`` on the result of
        :meth:`Locator._find_immediate`.  If the element is missing or stale,
        returns ``False`` so the outer ``_run`` loop can retry.

        **Not used** for ``to_be_visible`` / ``to_be_enabled`` — those
        delegate to ``Locator.is_visible()`` / ``is_enabled()`` which
        intentionally let ``NoSuchElementException`` propagate so that
        negated assertions (``not_.to_be_enabled()``) retry correctly.
        """
        from selenium.common.exceptions import (
            NoSuchElementException,
            StaleElementReferenceException,
        )

        try:
            element = self._locator._find_immediate()
            return eval_fn(element)
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    # -- public assertion methods ----------------------------------------- #

    def to_have_text(self, expected: str) -> None:
        """Assert that the element's text content contains *expected*.

        Uses ``_find_immediate()`` via ``_evaluate`` to avoid nested
        AutoWait — calling ``locator.text()`` would block for up to
        ``Timeout.DEFAULT`` inside its own wait, swallowing the assertion
        timeout.
        """
        self._run(
            lambda: self._evaluate(lambda el: expected in el.text),
            f"Expected element to have text '{expected}'",
        )

    def to_be_visible(self) -> None:
        """Assert that the element is visible on the page.

        Delegates to ``Locator.is_visible()`` which lets
        ``NoSuchElementException`` propagate — ensuring
        ``not_.to_be_visible()`` retries for missing elements.
        """
        self._run(
            lambda: self._locator.is_visible(),
            "Expected element to be visible",
        )

    def to_be_enabled(self) -> None:
        """Assert that the element is enabled.

        Delegates to ``Locator.is_enabled()`` which lets
        ``NoSuchElementException`` propagate — ensuring
        ``not_.to_be_enabled()`` retries for missing elements.
        """
        self._run(
            lambda: self._locator.is_enabled(),
            "Expected element to be enabled",
        )

    def to_have_attribute(self, name: str, value: str) -> None:
        """Assert that the element has attribute *name* equal to *value*.

        Uses ``_find_immediate()`` via ``_evaluate`` to avoid nested
        AutoWait — calling ``locator.get_attribute()`` would block for up
        to ``Timeout.DEFAULT`` inside its own wait, swallowing the assertion
        timeout.
        """
        self._run(
            lambda: self._evaluate(lambda el: el.get_attribute(name) == value),
            f"Expected element to have attribute '{name}' = '{value}'",
        )


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

    def _run(self, condition_fn, msg: str) -> None:
        """Retry *condition_fn* using :class:`AutoWait`."""
        from pylenium.waits.auto_wait import AutoWait
        from selenium.common.exceptions import TimeoutException

        driver = getattr(self._page, "_driver", None) or getattr(self._page, "driver", None)
        if not driver:
            raise ValueError("WebDriver not available for assertion retry")

        auto_wait = AutoWait(driver, timeout=self._timeout, polling=self._polling)

        try:
            auto_wait.until(
                lambda _: condition_fn() != self._is_negated,
                msg=msg,
            )
        except TimeoutException:
            negated_msg = " NOT" if self._is_negated else ""
            raise AssertionError(
                f"Assertion failed after {self._timeout}s:{negated_msg} {msg}"
            )

    def to_have_url(self, expected: str) -> None:
        """Assert that the page URL contains the expected string."""
        self._run(
            lambda: expected in self._page.url(),
            f"Expected page URL to contain '{expected}'",
        )

    def to_have_title(self, expected: str) -> None:
        """Assert that the page title contains the expected string."""
        self._run(
            lambda: expected in self._page.title(),
            f"Expected page title to contain '{expected}'",
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
