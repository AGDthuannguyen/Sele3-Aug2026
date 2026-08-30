from typing import Any

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions


class BrowserOptions:
    """Builder pattern for configuring browser options fluently."""

    def __init__(self, browser_type: str):
        self.browser_type = browser_type.lower()
        self._options: Any = self._init_options()

    def _init_options(self) -> Any:
        if self.browser_type == "chrome":
            return ChromeOptions()
        elif self.browser_type == "firefox":
            return FirefoxOptions()
        elif self.browser_type == "edge":
            return EdgeOptions()
        else:
            return ChromeOptions()  # Default fallback

    def headless(self, enabled: bool = True) -> "BrowserOptions":
        """Enable or disable headless mode."""
        if enabled:
            if self.browser_type in ("chrome", "edge"):
                self._options.add_argument("--headless=new")
            elif self.browser_type == "firefox":
                self._options.add_argument("-headless")
        return self

    def window_size(self, width: int, height: int) -> "BrowserOptions":
        """Set the initial window size."""
        self._options.add_argument(f"--window-size={width},{height}")
        return self

    def add_argument(self, arg: str) -> "BrowserOptions":
        """Add a raw argument to the browser options."""
        self._options.add_argument(arg)
        return self

    def build(self) -> Any:
        """Return the configured options object."""
        return self._options
