"""Lazy selectors: resolve once per poll, then check readiness and act."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    InvalidElementStateException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from pylenium.waits.auto_wait import AutoWait

T = TypeVar("T")


def _parse_selector(selector: str) -> tuple[str, str]:
    """Recognize XPath prefixes; otherwise use CSS."""
    if selector.startswith(("/", "(", "./")):
        return By.XPATH, selector
    return By.CSS_SELECTOR, selector


def _is_editable(element: WebElement) -> bool:
    """Wait for editable state, but reject targets that fill() cannot accept."""
    tag = element.tag_name.lower()
    if tag == "input":
        input_type = element.get_property("type")
        if input_type in {"button", "checkbox", "color", "file", "hidden",
                          "image", "radio", "range", "reset", "submit"}:
            raise ValueError(f"fill() does not support input type {input_type!r}")
    elif tag != "textarea" and not element.get_property("isContentEditable"):
        raise ValueError("fill() requires an input, textarea, or contenteditable element")

    if not EC.element_to_be_clickable(element)(None):
        return False
    return tag not in {"input", "textarea"} or element.get_dom_attribute("readonly") is None


class Locator:
    """Store a selector, optional parent and index; never cache a WebElement.

    Actions wait and retry transient failures. Immediate queries do not wait.
    Invalid selectors, invalid arguments and broken sessions propagate unchanged.
    """

    def __init__(self, selector: str, driver: WebDriver | None = None,
                 parent: Locator | None = None, index: int | None = None):
        if index is not None and (isinstance(index, bool) or not isinstance(index, int)):
            raise TypeError("index must be a non-negative integer")
        if index is not None and index < 0:
            raise ValueError("index must be a non-negative integer")
        self._driver = driver
        self._selector = selector
        self._parent = parent
        self._index = index
        self._by, self._value = _parse_selector(selector)

    def click(self) -> None:
        """Wait for visible/enabled, then click; retry stale or obstructed targets.

        A successful click is never repeated. Other driver failures propagate.
        """
        self._wait_and_apply(
            lambda element: element.click(),
            description="click",
            ready=lambda element: bool(EC.element_to_be_clickable(element)(None)),
            retry_exceptions=(ElementClickInterceptedException, ElementNotInteractableException),
        )

    def fill(self, text: str) -> None:
        """Replace editable content with text, retrying clear/send_keys as a unit.

        Hidden, disabled and readonly controls wait until ready. Each retry
        resolves again and clears before typing, including after partial input.
        Unsupported targets raise ValueError; non-string text raises TypeError.
        State changes during clear/send_keys retry; invalid arguments and session
        failures propagate. Retries may repeat input/change events.
        """
        if not isinstance(text, str):
            raise TypeError("fill() text must be a string")

        def replace_text(element: WebElement) -> None:
            element.clear()
            if text:
                element.send_keys(text)

        self._wait_and_apply(
            replace_text,
            description="fill",
            ready=_is_editable,
            retry_exceptions=(InvalidElementStateException,),
        )

    def text(self) -> str:
        """Wait for visible text; an empty string is a valid result."""
        return self._wait_and_apply(
            lambda element: element.text,
            description="read text",
            ready=lambda element: bool(EC.visibility_of(element)(None)),
        )

    def get_attribute(self, name: str) -> str | None:
        """Wait for presence and read Selenium's attribute/property value.

        None means the attribute is absent, not that the element is absent.
        """
        return self._wait_and_apply(
            lambda element: element.get_attribute(name),
            description=f"read attribute {name!r}",
        )

    def is_visible(self) -> bool:
        """Read visibility without waiting. Missing raises; stale returns False.

        This snapshot is not a retry predicate; assertions resolve independently.
        """
        try:
            return self._find_element().is_displayed()
        except StaleElementReferenceException:
            return False

    def is_enabled(self) -> bool:
        """Read enabled state without waiting. Missing raises; stale returns False."""
        try:
            return self._find_element().is_enabled()
        except StaleElementReferenceException:
            return False

    def locator(self, selector: str) -> Locator:
        """Create a lazy child selector within this element."""
        return Locator(selector, driver=self._driver, parent=self)

    def nth(self, index: int) -> Locator:
        """Select a non-negative index; actions wait until that element exists."""
        return Locator(self._selector, driver=self._driver, parent=self._parent, index=index)

    def first(self) -> Locator:
        """Select the first matching element."""
        return self.nth(0)

    def all(self) -> list[Locator]:
        """Snapshot the match count and return lazy indexed locators; do not wait."""
        return [self.nth(index) for index in range(self.count())]

    def count(self) -> int:
        """Count selector matches immediately, retaining the existing collection semantics."""
        return len(self._find_elements())

    def _resolve_driver(self) -> WebDriver:
        """Use this locator's driver, or inherit it from the parent."""
        if self._driver is not None:
            return self._driver
        if self._parent is not None:
            return self._parent._resolve_driver()
        raise ValueError("WebDriver instance not provided to Locator")

    def _find_elements(self) -> list[WebElement]:
        """Query the current scope once. Resolve the parent again on every call."""
        scope = self._parent._find_element() if self._parent is not None else self._resolve_driver()
        return scope.find_elements(self._by, self._value)

    def _find_element(self) -> WebElement:
        """Resolve one element immediately; no wait or readiness checks here.

        Missing matches/index raise NoSuchElementException. Stale references
        propagate so the caller can retry the entire parent/child lookup.
        """
        elements = self._find_elements()
        index = self._index if self._index is not None else 0
        if index >= len(elements):
            raise NoSuchElementException(f"Cannot find {self!r}")
        return elements[index]

    def _wait_and_apply(
        self,
        operation: Callable[[WebElement], T],
        *,
        description: str,
        ready: Callable[[WebElement], bool] | None = None,
        retry_exceptions: tuple[type[Exception], ...] = (),
    ) -> T:
        """Own the single action wait: resolve, check readiness, apply operation.

        Only missing/stale and the operation's explicit transient errors retry.
        A one-item tuple carries successful results even when they are None/"".
        """
        wait = AutoWait(
            self._resolve_driver(),
            ignored_exceptions=(NoSuchElementException, StaleElementReferenceException) + retry_exceptions,
        )

        def attempt(_: WebDriver) -> tuple[T] | bool:
            element = self._find_element()
            if ready is not None and not ready(element):
                return False
            return (operation(element),)

        result = wait.until(attempt, msg=f"Failed to {description}: {self!r}")
        return result[0]

    def __repr__(self) -> str:
        parent = f", parent={self._parent!r}" if self._parent is not None else ""
        index = f", index={self._index}" if self._index is not None else ""
        return f"Locator(selector={self._selector!r}{parent}{index})"
