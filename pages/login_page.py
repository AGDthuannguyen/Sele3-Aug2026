"""Login form on https://the-internet.herokuapp.com/login."""

from pylenium import BasePage, Page


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self.username = page.locator("#username")
        self.password = page.locator("#password")
        # The site uses a native button without an explicit role attribute.
        self.submit = page.locator("button[type='submit']")
        self.message = page.locator("#flash")

    def is_loaded(self) -> bool:
        return self.username.is_visible()

    def login(self, username: str, password: str) -> None:
        """Submit credentials; the caller decides which outcome to assert."""
        self.username.fill(username)
        self.password.fill(password)
        self.submit.click()
