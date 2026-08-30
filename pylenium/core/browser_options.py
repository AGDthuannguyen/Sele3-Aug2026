"""Builder pattern for configuring browser options fluently.

Delegates browser-specific logic to BrowserStrategy classes,
keeping this class clean and free of if-else branching.
"""

from __future__ import annotations

from selenium.webdriver.common.options import ArgOptions

from pylenium.core.browser_strategy import BrowserStrategy, get_strategy


class BrowserOptions:
    """Builder for browser options with a fluent API."""

    def __init__(self, browser_type: str):
        self._strategy: BrowserStrategy = get_strategy(browser_type)
        self._options: ArgOptions | None = self._strategy.create_options()
        self._headless: bool = False

    def headless(self, enabled: bool = True) -> BrowserOptions:
        """Enable or disable headless mode."""
        self._headless = enabled
        return self

    def window_size(self, width: int, height: int) -> BrowserOptions:
        """Set the initial window size."""
        if self._options is not None:
            self._options.add_argument(f"--window-size={width},{height}")
        return self

    def add_argument(self, arg: str) -> BrowserOptions:
        """Add a raw argument to the browser options."""
        if self._options is not None:
            self._options.add_argument(arg)
        return self

    def build(self) -> ArgOptions | None:
        """Apply all deferred settings and return the configured options."""
        if self._headless:
            self._strategy.apply_headless(self._options)
        return self._options

    @property
    def strategy(self) -> BrowserStrategy:
        """Expose the strategy for driver creation."""
        return self._strategy
