"""Automatic waiting logic for the Pylenium framework.

AutoWait wraps Selenium's WebDriverWait to provide transparent,
configurable waiting before element interactions. Timeout and
polling interval are read from Dynaconf settings.
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from pylenium.config.config import settings
from pylenium.waits.conditions import WaitCondition
from pylenium.constants.timeouts import Timeout

if TYPE_CHECKING:
    from pylenium.core.locator import Locator


class AutoWait:
    """Provides automatic waiting for element conditions."""

    def __init__(self, driver: WebDriver, timeout: float | None = None,
                 polling: float | None = None):
        self._driver = driver
        self._timeout = timeout or Timeout.DEFAULT.value
        self._polling = polling or settings.get("waits.polling_interval", 0.5)
        self._ignored = (StaleElementReferenceException, NoSuchElementException)

    @staticmethod
    def _to_tuple(locator: Locator | tuple) -> tuple:
        """Convert a Locator or tuple into a (by, value) tuple."""
        if isinstance(locator, tuple):
            return locator
        return locator._by, locator._value

    def for_condition(self, locator: Locator | tuple,
                      condition: WaitCondition) -> WebElement:
        """Wait until the element satisfies the given WaitCondition.

        Args:
            locator: A ``Locator`` instance or a ``(by, value)`` tuple.
            condition: The ``WaitCondition`` to wait for.

        Returns:
            The matching WebElement.
        """
        return self._wait_for(condition, self._to_tuple(locator))

    def until(self, condition_fn: Callable, msg: str = "") -> Any:
        """Wait until a custom condition function returns a truthy value.

        Args:
            condition_fn: A callable that takes a WebDriver and returns
                          a truthy value when the condition is met.
            msg: Optional message for the TimeoutException.

        Returns:
            The truthy result of the condition function.

        Raises:
            TimeoutException: If the condition is not met within the timeout.
        """
        wait = WebDriverWait(
            self._driver, self._timeout, self._polling, ignored_exceptions=self._ignored
        )
        return wait.until(condition_fn, message=msg)

    def _wait_for(self, condition: WaitCondition, locator_tuple: tuple) -> Any:
        """Internal helper to wait for a specific WaitCondition.

        Args:
            condition: The WaitCondition to wait for.
            locator_tuple: A (By, value) tuple.

        Returns:
            The result of the expected condition (usually a WebElement).

        Raises:
            TimeoutException: If the condition is not met within the timeout.
        """
        wait = WebDriverWait(
            self._driver, self._timeout, self._polling, ignored_exceptions=self._ignored
        )
        ec = condition.get_expected_condition(locator_tuple)
        return wait.until(ec, message=(
            f"Timed out after {self._timeout}s waiting for element "
            f"{locator_tuple} to be {condition.value}"
        ))
