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

from pylenium.waits.auto_wait import AutoWait


def _parse_selector(selector: str) -> tuple[str, str]:
    """Auto-detect selector type (CSS or XPath) based on the selector string.

    Selectors starting with '/', '(' or './' are treated as XPath.
    Everything else is treated as CSS.
    """
    if selector.startswith(('/', '(')) or selector.startswith('./') or selector.startswith('.//'):
        return By.XPATH, selector
    return By.CSS_SELECTOR, selector


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

        Retries once if a ``StaleElementReferenceException`` occurs.
        """
        try:
            element = self._find_with_wait("clickable")
            element.click()
        except StaleElementReferenceException:
            # Re‑find and retry once
            element = self._find_with_wait("clickable")
            element.click()

    def fill(self, text: str) -> None:
        """Wait for the element to be visible, clear it, then type text.

        Retries once on ``StaleElementReferenceException``.
        """
        try:
            element = self._find_with_wait("visible")
            element.clear()
            element.send_keys(text)
        except StaleElementReferenceException:
            element = self._find_with_wait("visible")
            element.clear()
            element.send_keys(text)

    def text(self) -> str:
        """Wait for the element to be visible and return its text content."""
        element = self._find_with_wait("visible")
        return element.text

    def is_visible(self) -> bool:
        """Check if the element is currently visible without waiting.

        Returns ``True`` if displayed, ``False`` otherwise.
        """
        try:
            element = self._find_immediate()
            return element.is_displayed()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def is_enabled(self) -> bool:
        """Check if the element is currently enabled without waiting.

        Returns ``True`` if enabled, ``False`` otherwise.
        """
        try:
            element = self._find_immediate()
            return element.is_enabled()
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    def get_attribute(self, name: str) -> str | None:
        """Wait for the element to be present and return its attribute value.

        Args:
            name: The attribute name.

        Returns:
            The attribute value, or None if not found.
        """
        element = self._find_with_wait("present")
        return element.get_attribute(name)

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
        elements = self._find_all()
        return [
            Locator(self._selector, driver=self._driver, parent=self._parent, index=i)
            for i in range(len(elements))
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

    def _find_with_wait(self, condition: str) -> WebElement:
        """Find the element with auto-wait.

        Args:
            condition: One of 'visible', 'clickable', 'present'.

        Returns:
            The found WebElement.
        """
        auto_wait = AutoWait(self._driver)

        if self._parent is not None:
            # Child scope: find parent first, then search within it
            parent_element = self._parent._find_with_wait("present")
            return self._wait_within_parent(parent_element, condition)

        if self._index is not None:
            # Indexed element: find all, then pick by index
            auto_wait._for_present((self._by, self._value))
            elements = self._find_all()
            if self._index >= len(elements):
                raise IndexError(
                    f"Index {self._index} out of range for "
                    f"selector '{self._selector}' (found {len(elements)} elements)"
                )
            return elements[self._index]

        # Normal: auto-wait on the selector directly
        wait_methods = {
            "visible": auto_wait._for_visible,
            "clickable": auto_wait._for_clickable,
            "present": auto_wait._for_present,
        }
        
        wait_func = wait_methods.get(condition, auto_wait._for_present)
        return wait_func((self._by, self._value))

    def _wait_within_parent(self, parent_element: WebElement,
                            condition: str) -> WebElement:
        """Wait for an element within a parent element's scope.

        Args:
            parent_element: The parent WebElement to search within.
            condition: The wait condition type.

        Returns:
            The found child WebElement.
        """
        auto_wait = AutoWait(self._driver)

        def _find_child(driver):
            elements = parent_element.find_elements(self._by, self._value)
            if not elements:
                return False
            element = elements[self._index] if self._index is not None else elements[0]
            if condition == "visible" and not element.is_displayed():
                return False
            if condition == "clickable" and (not element.is_displayed() or not element.is_enabled()):
                return False
            return element

        return auto_wait.until(
            _find_child,
            msg=f"Child element '{self._selector}' not {condition} within parent"
        )

    def _find_immediate(self) -> WebElement:
        """Find the element immediately without waiting.

        Returns:
            The found WebElement.

        Raises:
            NoSuchElementException: If the element is not found.
        """
        if self._parent is not None:
            parent_element = self._parent._find_immediate()
            elements = parent_element.find_elements(self._by, self._value)
        else:
            elements = self._driver.find_elements(self._by, self._value)

        if not elements:
            raise NoSuchElementException(f"Cannot find element: {self._selector}")
        if self._index is not None:
            if self._index >= len(elements):
                raise IndexError(f"Index {self._index} out of range for selector '{self._selector}'")
            return elements[self._index]
        return elements[0]

    def _find_all(self) -> list[WebElement]:
        """Find all matching elements immediately.

        Returns:
            A list of matching WebElements.
        """
        return self._find_all_raw()

    def _find_all_raw(self) -> list[WebElement]:
        """Raw find_elements call, respecting parent scope.

        Returns:
            A list of matching WebElements.
        """
        if self._parent is not None:
            parent_element = self._parent._find_immediate()
            return parent_element.find_elements(self._by, self._value)
        return self._driver.find_elements(self._by, self._value)

    def __repr__(self) -> str:
        parent_info = f", parent={self._parent!r}" if self._parent else ""
        index_info = f", index={self._index}" if self._index is not None else ""
        return f"Locator(selector='{self._selector}'{parent_info}{index_info})"
