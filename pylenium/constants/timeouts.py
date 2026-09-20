from enum import Enum

class Timeout(Enum):
    """Centralized timeout values (in seconds)."""
    DEFAULT = 10  # generic waits
    ASSERTION = 5  # assertion retries
