"""Wait condition types for the AutoWait system.

Each condition maps to a Selenium expected_conditions function,
defining what state an element must reach before an action proceeds.
"""

from enum import Enum

from selenium.webdriver.support import expected_conditions as EC


class WaitCondition(Enum):
    """Enumeration of element wait conditions."""

    PRESENT = "present"
    VISIBLE = "visible"
    CLICKABLE = "clickable"
    INVISIBLE = "invisible"

    def get_expected_condition(self, locator_tuple: tuple):
        """Return the Selenium expected_conditions callable for this condition.

        Args:
            locator_tuple: A (By, value) tuple identifying the element.

        Returns:
            A callable expected condition for use with WebDriverWait.
        """
        mapping = {
            WaitCondition.PRESENT: EC.presence_of_element_located,
            WaitCondition.VISIBLE: EC.visibility_of_element_located,
            WaitCondition.CLICKABLE: EC.element_to_be_clickable,
            WaitCondition.INVISIBLE: EC.invisibility_of_element_located,
        }
        return mapping[self](locator_tuple)
