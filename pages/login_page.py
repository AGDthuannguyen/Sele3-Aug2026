"""Login form on Automation Exercise."""

from pylenium import BasePage, Page


class LoginPage(BasePage):
    URL = "/login"

    def __init__(self, page: Page):
        super().__init__(page)
        self._email = page.locator("[data-qa='login-email']")
        self._password = page.locator("[data-qa='login-password']")
        self._submit = page.locator("[data-qa='login-button']")

    def is_loaded(self) -> bool:
        return self._email.is_visible()

    def login(self, email: str, password: str) -> None:
        """Submit credentials; the caller decides which outcome to assert."""
        self._email.fill(email)
        self._password.fill(password)
        self._submit.click()
