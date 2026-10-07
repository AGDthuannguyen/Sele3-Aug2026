"""Check that unsupported Safari headless runs fail before driver creation."""

import pytest

from pylenium.core.browser_options import BrowserOptions


def test_safari_headless_is_rejected():
    with pytest.raises(ValueError, match="Safari does not support headless mode"):
        BrowserOptions("safari").headless().build()
