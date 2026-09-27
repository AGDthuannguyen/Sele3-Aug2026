"""Retry assertions without treating missing or stale reads as boolean results.

Visibility allows absence only in its negative form. Enabled/text/attribute
assertions require an existing, readable element in both forms. Stale reads
always retry. String assertions retain substring matching.
"""

from __future__ import annotations

from collections.abc import Callable
from copy import copy
from typing import overload

from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.config.config import settings
from pylenium.core.locator import Locator
from pylenium.core.page import Page
from pylenium.waits.auto_wait import AutoWait


def _assertion_wait(driver: WebDriver, timeout: float | None) -> AutoWait:
    """Read assertion settings once and reuse AutoWait's validation."""
    return AutoWait(
        driver,
        timeout=settings.get("assertions.timeout", 5.0) if timeout is None else timeout,
        polling=settings.get("assertions.polling_interval", 0.25),
        ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
    )


def _wait_for_assertion(
    wait: AutoWait,
    check: Callable[[], tuple[bool, str]],
    message: str,
) -> None:
    """Poll a complete assertion decision; never invert missing/stale outcomes.

    Each check owns its positive/negative semantics. Only missing/stale reads
    retry here. Other failures propagate; diagnostics use the last poll only.
    """
    last_state = "not evaluated"
    read_timeout: TimeoutException | None = None

    def poll(_: WebDriver) -> bool:
        nonlocal last_state, read_timeout
        try:
            passed, last_state = check()
            return passed
        except (NoSuchElementException, StaleElementReferenceException) as error:
            last_state = type(error).__name__
            return False
        except TimeoutException as error:
            # A driver command timeout is not the assertion's polling deadline.
            read_timeout = error
            raise

    try:
        wait.until(poll, msg=message)
    except TimeoutException as error:
        if error is read_timeout:
            raise
        raise AssertionError(f"{message}\nLast state: {last_state}") from error


class LocatorAssertions:
    """Assert an element's state. Absence is allowed only for not_.to_be_visible()."""

    def __init__(self, locator: Locator, timeout: float | None = None,
                 is_negated: bool = False):
        self._locator = locator
        self._wait = _assertion_wait(locator._resolve_driver(), timeout)
        self._is_negated = is_negated

    @property
    def not_(self) -> LocatorAssertions:
        """Return the opposite expectation without changing the original or its settings."""
        negated = copy(self)
        negated._is_negated = not self._is_negated
        return negated

    def to_be_visible(self) -> None:
        """Require visibility; the negative form also accepts an absent element."""
        expected = not self._is_negated

        def check() -> tuple[bool, str]:
            try:
                visible = self._locator._find_element().is_displayed()
            except NoSuchElementException:
                return self._is_negated, "missing"
            return visible == expected, f"visible={visible}"

        _wait_for_assertion(
            self._wait, check,
            f"Expected {self._locator!r} to have visible={expected}",
        )

    def to_be_enabled(self) -> None:
        """Require an existing enabled/disabled element; missing never passes."""
        expected = not self._is_negated

        def check() -> tuple[bool, str]:
            enabled = self._locator._find_element().is_enabled()
            return enabled == expected, f"enabled={enabled}"

        _wait_for_assertion(
            self._wait, check,
            f"Expected {self._locator!r} to have enabled={expected}",
        )

    def to_have_text(self, expected: str) -> None:
        """Require readable text containing (or not containing) the substring."""
        def check() -> tuple[bool, str]:
            actual = self._locator._find_element().text
            passed = expected not in actual if self._is_negated else expected in actual
            return passed, f"text={actual!r}"

        comparison = "not contain" if self._is_negated else "contain"
        _wait_for_assertion(
            self._wait, check,
            f"Expected {self._locator!r} to {comparison} text {expected!r}",
        )

    def to_have_attribute(self, name: str, value: str) -> None:
        """Require a readable element's attribute/property to equal (or differ from) value.

        A missing attribute is None and may satisfy the negative form.
        A missing element cannot satisfy either form.
        """
        def check() -> tuple[bool, str]:
            actual = self._locator._find_element().get_attribute(name)
            passed = actual != value if self._is_negated else actual == value
            return passed, f"attribute {name!r}={actual!r}"

        comparison = "not equal" if self._is_negated else "equal"
        _wait_for_assertion(
            self._wait, check,
            f"Expected {self._locator!r} attribute {name!r} to {comparison} {value!r}",
        )


class PageAssertions:
    """Retry title/URL substring checks; driver failures are not assertion mismatches."""

    def __init__(self, page: Page, timeout: float | None = None,
                 is_negated: bool = False):
        self._page = page
        self._wait = _assertion_wait(page._driver, timeout)
        self._is_negated = is_negated

    @property
    def not_(self) -> PageAssertions:
        """Return the opposite expectation, preserving timeout and polling settings."""
        negated = copy(self)
        negated._is_negated = not self._is_negated
        return negated

    def to_have_url(self, expected: str) -> None:
        """Require the URL to contain (or not contain) the substring."""
        def check() -> tuple[bool, str]:
            actual = self._page.url()
            passed = expected not in actual if self._is_negated else expected in actual
            return passed, f"url={actual!r}"

        comparison = "not contain" if self._is_negated else "contain"
        _wait_for_assertion(self._wait, check, f"Expected page URL to {comparison} {expected!r}")

    def to_have_title(self, expected: str) -> None:
        """Require the title to contain (or not contain) the substring."""
        def check() -> tuple[bool, str]:
            actual = self._page.title()
            passed = expected not in actual if self._is_negated else expected in actual
            return passed, f"title={actual!r}"

        comparison = "not contain" if self._is_negated else "contain"
        _wait_for_assertion(self._wait, check, f"Expected page title to {comparison} {expected!r}")


@overload
def expect(target: Locator, *, timeout: float | None = None) -> LocatorAssertions: ...


@overload
def expect(target: Page, *, timeout: float | None = None) -> PageAssertions: ...


def expect(target: Locator | Page, *, timeout: float | None = None) -> LocatorAssertions | PageAssertions:
    """Create retrying assertions for a Locator or Page; timeout is in seconds."""
    if isinstance(target, Locator):
        return LocatorAssertions(target, timeout=timeout)
    if isinstance(target, Page):
        return PageAssertions(target, timeout=timeout)
    raise TypeError(f"expect() requires a Locator or Page, got {type(target).__name__}")
