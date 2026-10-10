"""Collect retrying assertion failures until a test block finishes."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import ParamSpec


P = ParamSpec("P")


class _SoftAssertions:
    def __init__(self) -> None:
        self._failures: list[str] = []

    def check(self, assertion: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
        """Run one assertion and record its failure while allowing later checks."""
        try:
            assertion(*args, **kwargs)
        except AssertionError as error:
            self._failures.append(str(error))

    def _raise_if_failed(self) -> None:
        if self._failures:
            details = "\n\n".join(
                f"{number}. {message}" for number, message in enumerate(self._failures, 1)
            )
            raise AssertionError(f"{len(self._failures)} soft assertion(s) failed:\n{details}")


@contextmanager
def soft_assertions() -> Iterator[_SoftAssertions]:
    """Collect check() failures and report them together when the block exits.

    Unexpected exceptions leave the block immediately and retain their type.
    """
    collector = _SoftAssertions()
    yield collector
    collector._raise_if_failed()
