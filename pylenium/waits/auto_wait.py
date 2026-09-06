"""Automatic waiting logic for the Pylenium framework.

AutoWait wraps Selenium's WebDriverWait to provide transparent,
configurable waiting before element interactions. Timeout and
polling interval are read from Dynaconf settings.
"""

from __future__ import annotations

from typing import Any, Callable

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from pylenium.config.config import settings
from pylenium.waits.conditions import WaitCondition


class AutoWait:
    """Provides automatic waiting for element conditions."""

    def __init__(self, driver: WebDriver, timeout: float | None = None,
                 polling: float | None = None):
        self._driver = driver
        self._timeout = timeout or settings.get("waits.timeout", 10)
        self._polling = polling or settings.get("waits.polling_interval", 0.5)

    def _for_visible(self, by: str, value: str) -> WebElement:
        """Wait until an element is visible and return it.

        Args:
            by: The Selenium By strategy (e.g., By.CSS_SELECTOR).
            value: The selector value.

        Returns:
            The visible WebElement.
        """
        return self._wait_for(WaitCondition.VISIBLE, (by, value))

    def _for_clickable(self, by: str, value: str) -> WebElement:
        """Wait until an element is clickable and return it.

        Args:
            by: The Selenium By strategy.
            value: The selector value.

        Returns:
            The clickable WebElement.
        """
        return self._wait_for(WaitCondition.CLICKABLE, (by, value))

    def _for_present(self, by: str, value: str) -> WebElement:
        """Wait until an element is present in the DOM and return it.

        Args:
            by: The Selenium By strategy.
            value: The selector value.

        Returns:
            The present WebElement.
        """
        return self._wait_for(WaitCondition.PRESENT, (by, value))

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
        wait = WebDriverWait(self._driver, self._timeout, self._polling)
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
        wait = WebDriverWait(self._driver, self._timeout, self._polling)
        ec = condition.get_expected_condition(locator_tuple)
        return wait.until(ec, message=(
            f"Timed out after {self._timeout}s waiting for element "
            f"{locator_tuple} to be {condition.value}"
        ))
