from selenium import webdriver
from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.core.browser_options import BrowserOptions


class BrowserFactory:
    """Factory pattern for creating WebDriver instances."""

    @staticmethod
    def create(browser_type: str, options: BrowserOptions | None = None) -> WebDriver:
        """Create and return a WebDriver instance for the specified browser type.

        Args:
            browser_type: The name of the browser (e.g., 'chrome', 'firefox').
            options: Optional BrowserOptions instance.

        Returns:
            A Selenium WebDriver instance.
        """
        browser_type = browser_type.lower()
        opts = options.build() if options else BrowserOptions(browser_type).build()

        if browser_type == "chrome":
            return webdriver.Chrome(options=opts)
        elif browser_type == "firefox":
            return webdriver.Firefox(options=opts)
        elif browser_type == "edge":
            return webdriver.Edge(options=opts)
        elif browser_type == "safari":
            # Safari doesn't use standard options in the same way
            return webdriver.Safari()
        else:
            raise ValueError(f"Unsupported browser type: {browser_type}")
