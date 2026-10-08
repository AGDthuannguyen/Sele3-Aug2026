"""Page Object template with one wait for page readiness."""

from abc import ABC, abstractmethod
from typing import Self

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

from pylenium.core.page import Page
from pylenium.waits.auto_wait import AutoWait


class BasePage(ABC):
    """Define lazy locators in __init__ and a non-waiting is_loaded check.

    open() navigates using WebDriver's page-load timeout. Call
    wait_until_loaded(timeout=...) separately to wait for application readiness.
    """

    URL: str = ""

    def __init__(self, page: Page):
        self.page = page

    @abstractmethod
    def is_loaded(self) -> bool:
        """Check readiness once; do not call waiting actions or expect() here."""

    def wait_until_loaded(self, *, timeout: float | None = None) -> Self:
        """Retry missing/stale readiness checks under one timeout budget."""
        AutoWait(
            self.page._driver, timeout=timeout,
            ignored_exceptions=(NoSuchElementException, StaleElementReferenceException),
        ).until(lambda _: self.is_loaded(), msg=f"{type(self).__name__} did not load")
        return self

    def open(self) -> Self:
        """Navigate to URL without starting a second readiness wait."""
        if not self.URL:
            raise ValueError("Define a non-empty URL on the page object")
        self.page.goto(self.URL)
        return self
