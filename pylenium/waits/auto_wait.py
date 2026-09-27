"""Automatic waiting logic for the Pylenium framework.

AutoWait wraps Selenium's WebDriverWait to provide transparent,
configurable waiting before element interactions. Timeout and
polling interval are read from Dynaconf settings.
"""

from __future__ import annotations

from typing import Any, Callable

from selenium.common.exceptions import (
    TimeoutException,
    StaleElementReferenceException,
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait

from pylenium.config.config import settings

class AutoWait:
    """Provides automatic waiting for element conditions."""

    def __init__(self, driver: WebDriver, timeout: float | None = None,
                 polling: float | None = None, *,
                 ignored_exceptions: tuple[type[Exception], ...] | None = None):
        """Configure retry errors in addition to Selenium's mandatory missing-element default.

        Passing a tuple replaces Pylenium's extra defaults. As in WebDriverWait,
        NoSuchElementException always retries, including when timeout is zero.
        """
        self._driver = driver

        t = settings.get("waits.timeout", 10.0) if timeout is None else timeout
        p = settings.get("waits.polling_interval", 0.5) if polling is None else polling

        if t < 0:
            raise ValueError("Timeout cannot be negative")
        if p <= 0:
            raise ValueError("Polling interval must be > 0")

        self._timeout = t
        self._polling = p
        extra_errors = ignored_exceptions if ignored_exceptions is not None else (
            StaleElementReferenceException,
            NoSuchElementException,
            ElementClickInterceptedException,
            ElementNotInteractableException,
        )
        self._ignored = tuple(dict.fromkeys((NoSuchElementException,) + extra_errors))

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
        if self._timeout == 0:
            try:
                result = condition_fn(self._driver)
                if result:
                    return result
            except self._ignored:
                pass
            raise TimeoutException(msg)

        wait = WebDriverWait(
            self._driver, self._timeout, self._polling, ignored_exceptions=self._ignored
        )
        return wait.until(condition_fn, message=msg)
