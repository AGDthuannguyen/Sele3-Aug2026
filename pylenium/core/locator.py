"""Lazy element locator with automatic waiting.

Locator does NOT query the DOM on creation. It only finds the element
when an action (click, fill, text, etc.) is performed. This prevents
StaleElementReferenceException and makes it safe to define locators
in __init__ of Page Objects.
"""

from __future__ import annotations

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from pylenium.constants.timeouts import Timeout
from pylenium.waits.auto_wait import AutoWait
from pylenium.waits.conditions import WaitCondition


ByType = str
"""Type alias for Selenium By strategy strings (e.g. ``By.CSS_SELECTOR``)."""


def _parse_selector(selector: str) -> tuple[ByType, str]:
    """Auto-detect selector type (CSS or XPath) based on the selector string.

    Selectors starting with ``/``, ``(``, ``./`` or ``.//`` are treated as XPath.
    Everything else is treated as CSS.
    """
    if selector.startswith(('/', '(', './', './/')):
        return By.XPATH, selector
    return By.CSS_SELECTOR, selector


def _check_condition(element: WebElement, condition: WaitCondition) -> bool:
    """Return True if the element satisfies the given WaitCondition.

    For ``PRESENT``, every element qualifies.
    For ``VISIBLE``, the element must be displayed.
    For ``CLICKABLE``, the element must be displayed **and** enabled.
    """
    if condition == WaitCondition.VISIBLE:
        return element.is_displayed()
    if condition == WaitCondition.CLICKABLE:
        return element.is_displayed() and element.is_enabled()
    return True  # PRESENT — just being in the DOM is enough


class Locator:
    """Lazy, auto-waiting element locator with Playwright-like API.

    Attributes:
        _driver: The Selenium WebDriver instance.
        _selector: The CSS/XPath selector string.
        _parent: Optional parent Locator for child-scoped searches.
        _index: Optional index for nth() element selection.
    """

    def __init__(self, selector: str, driver: WebDriver | None = None,
                 parent: Locator | None = None,
                 index: int | None = None):
        """Create a Locator.

        The driver can be omitted for class‑level definitions. It will be
        resolved lazily from the parent ``Locator`` (or a ``Page`` that
        binds it later).
        """
        self._driver = driver
        self._selector = selector
        self._parent = parent
        self._index = index
        self._by, self._value = _parse_selector(selector)

    def _resolve_driver(self) -> WebDriver:
        """Return the effective WebDriver, searching up the parent chain.

        Raises:
            ValueError: If no driver is available.
        """
        if self._driver is not None:
            return self._driver
        if self._parent is not None:
            return self._parent._resolve_driver()
        raise ValueError("WebDriver instance not provided to Locator")

    # -- Actions (auto-wait before executing) --

    def click(self) -> None:
        """Wait for the element to be clickable, then click it.

        Uses ``AutoWait.until`` so that any
        ``StaleElementReferenceException`` during the find-and-click
        sequence is automatically retried until timeout.
        """
        auto_wait = AutoWait(self._resolve_driver())

        def _click(driver):
            self._find_fresh_element(WaitCondition.CLICKABLE).click()
            return True

        auto_wait.until(_click, msg=f"Failed to click element: {self._selector}")

    def fill(self, text: str) -> None:
        """Wait for the element to be visible, clear it, then type text.

        Uses ``AutoWait.until`` so that any
        ``StaleElementReferenceException`` during the sequence is
        automatically retried until timeout.
        """
        auto_wait = AutoWait(self._resolve_driver())

        def _fill(driver):
            element = self._find_fresh_element(WaitCondition.VISIBLE)
            element.clear()
            element.send_keys(text)
            return True

        auto_wait.until(_fill, msg=f"Failed to fill element: {self._selector}")

    def text(self) -> str:
        """Wait for the element to be visible and return its text content.

        Uses ``AutoWait.until`` so that any
        ``StaleElementReferenceException`` is automatically retried.
        """
        auto_wait = AutoWait(self._resolve_driver())
        result: dict[str, str] = {}

        def _text(driver):
            result["value"] = self._find_fresh_element(WaitCondition.VISIBLE).text
            return True

        auto_wait.until(_text, msg=f"Failed to get text from element: {self._selector}")
        return result["value"]

    def is_visible(self) -> bool:
        """Check if the element is currently visible without waiting.

        Returns ``True`` if displayed, ``False`` otherwise.
        """
        try:
            return self._find_immediate().is_displayed()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def is_enabled(self) -> bool:
        """Check if the element is currently enabled without waiting.

        Returns ``True`` if enabled, ``False`` otherwise.
        """
        try:
            return self._find_immediate().is_enabled()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def get_attribute(self, name: str) -> str | None:
        """Wait for the element to be present and return its attribute value.

        Uses ``AutoWait.until`` so that any
        ``StaleElementReferenceException`` is automatically retried.

        Args:
            name: The attribute name.

        Returns:
            The attribute value, or None if not found.
        """
        auto_wait = AutoWait(self._resolve_driver())
        result: dict[str, str | None] = {}

        def _get_attr(driver):
            result["value"] = self._find_fresh_element(WaitCondition.PRESENT).get_attribute(name)
            return True

        auto_wait.until(
            _get_attr,
            msg=f"Failed to get attribute '{name}' from element: {self._selector}"
        )
        return result["value"]

    # -- Child scope --

    def locator(self, selector: str) -> Locator:
        """Create a new Locator scoped to this element.

        Args:
            selector: CSS or XPath selector relative to this element.

        Returns:
            A new child-scoped Locator.
        """
        return Locator(selector, driver=self._driver, parent=self)

    # -- Collection methods --

    def all(self) -> list[Locator]:
        """Find all matching elements and return a list of Locators.

        Returns:
            A list of Locator instances, one per matching element.
        """
        return [
            Locator(self._selector, driver=self._driver, parent=self._parent, index=i)
            for i in range(self.count())
        ]

    def first(self) -> Locator:
        """Return a Locator for the first matching element."""
        return self.nth(0)

    def nth(self, index: int) -> Locator:
        """Return a Locator for the element at the given index.

        Args:
            index: Zero-based index of the element.

        Returns:
            A new Locator targeting the element at the specified index.
        """
        return Locator(self._selector, driver=self._driver, parent=self._parent, index=index)

    def count(self) -> int:
        """Return the number of matching elements.

        Returns:
            The count of elements matching this locator.
        """
        return len(self._find_all())

    # -- Internal methods --

    def _find_with_wait(self, condition: WaitCondition) -> WebElement:
        """Find the element with auto-wait.

        Args:
            condition: The ``WaitCondition`` to wait for.

        Returns:
            The found WebElement.
        """
        auto_wait = AutoWait(self._resolve_driver(), timeout=Timeout.DEFAULT.value)

        if self._parent is not None:
            parent_element = self._parent._find_with_wait(WaitCondition.PRESENT)
            return self._wait_within_parent(parent_element, condition)

        if self._index is not None:
            return self._wait_for_indexed(auto_wait, condition)

        return auto_wait.for_condition(self, condition)

    def _wait_for_indexed(self, auto_wait: AutoWait,
                          condition: WaitCondition) -> WebElement:
        """Wait until enough elements exist, then pick by index.

        Continuously polls until ``len(elements) > self._index`` and the
        target element satisfies ``condition``. Raises ``TimeoutException``
        if the condition is not met within the timeout.
        """
        def _poll(driver):
            if self.count() <= self._index:
                return False
            element = self._find_all()[self._index]
            return element if _check_condition(element, condition) else False

        return auto_wait.until(
            _poll,
            msg=(
                f"Timed out waiting for element at index {self._index} "
                f"of selector '{self._selector}' to be {condition.value}"
            ),
        )

    def _wait_within_parent(self, parent_element: WebElement,
                            condition: WaitCondition) -> WebElement:
        """Wait for an element within a parent element's scope.

        Args:
            parent_element: The parent WebElement to search within.
            condition: The WaitCondition to satisfy.

        Returns:
            The found child WebElement.
        """
        auto_wait = AutoWait(self._resolve_driver())

        def _find_child(driver):
            elements = parent_element.find_elements(self._by, self._value)
            if not elements:
                return False
            element = elements[self._index] if self._index is not None else elements[0]
            return element if _check_condition(element, condition) else False

        return auto_wait.until(
            _find_child,
            msg=f"Child element '{self._selector}' not {condition.value} within parent"
        )

    def _find_immediate(self) -> WebElement:
        """Find the element immediately without waiting.

        Returns:
            The found WebElement.

        Raises:
            NoSuchElementException: If the element is not found.
        """
        driver = self._resolve_driver()
        if self._parent is not None:
            parent_element = self._parent._find_immediate()
            elements = parent_element.find_elements(self._by, self._value)
        else:
            elements = driver.find_elements(self._by, self._value)

        if not elements:
            raise NoSuchElementException(f"Cannot find element: {self._selector}")
        if self._index is not None:
            if self._index >= len(elements):
                raise IndexError(f"Index {self._index} out of range for selector '{self._selector}'")
            return elements[self._index]
        return elements[0]

    def _find_fresh_element(self, condition: WaitCondition) -> WebElement:
        """Find the element immediately and verify the given condition.

        This is intended for use inside an ``AutoWait.until`` loop so
        that ``StaleElementReferenceException`` raised here is caught by
        the outer ``WebDriverWait`` and retried automatically.

        Args:
            condition: The ``WaitCondition`` the element must satisfy.

        Returns:
            The matching ``WebElement``.

        Raises:
            NoSuchElementException: Propagated so ``WebDriverWait`` retries.
            StaleElementReferenceException: Propagated so ``WebDriverWait`` retries.
        """
        element = self._find_immediate()
        if not _check_condition(element, condition):
            raise NoSuchElementException(
                f"Element found but not {condition.value}: {self._selector}"
            )
        return element

    def _find_all(self) -> list[WebElement]:
        """Find all matching elements immediately.

        Returns:
            A list of matching WebElements.
        """
        if self._parent is not None:
            parent_element = self._parent._find_immediate()
            return parent_element.find_elements(self._by, self._value)
        return self._resolve_driver().find_elements(self._by, self._value)

    def __repr__(self) -> str:
        parent_info = f", parent={self._parent!r}" if self._parent else ""
        index_info = f", index={self._index}" if self._index is not None else ""
        return f"Locator(selector='{self._selector}'{parent_info}{index_info})"
