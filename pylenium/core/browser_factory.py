"""Factory pattern for creating WebDriver instances.

Delegates to BrowserStrategy via BrowserOptions, eliminating
duplicated if-else blocks for browser type selection.
"""

from selenium.webdriver.remote.webdriver import WebDriver

from pylenium.core.browser_options import BrowserOptions


class BrowserFactory:
    """Factory for creating WebDriver instances."""

    @staticmethod
    def create(browser_type: str, options: BrowserOptions | None = None) -> WebDriver:
        """Create and return a WebDriver instance for the specified browser type.

        Args:
            browser_type: The name of the browser (e.g., 'chrome', 'firefox').
            options: Optional BrowserOptions instance.

        Returns:
            A Selenium WebDriver instance.
        """
        if options is None:
            options = BrowserOptions(browser_type)

        built_options = options.build()
        return options.strategy.create_driver(built_options)
