"""Login form on https://the-internet.herokuapp.com/login."""

from pylenium import BasePage, Page


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self._username = page.locator("#username")
        self._password = page.locator("#password")
        # The site uses a native button without an explicit role attribute.
        self._submit = page.locator("button[type='submit']")

    def is_loaded(self) -> bool:
        return self._username.is_visible()

    def login(self, username: str, password: str) -> None:
        """Submit credentials; the caller decides which outcome to assert."""
        self._username.fill(username)
        self._password.fill(password)
        self._submit.click()
