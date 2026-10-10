"""Collect retrying assertion failures until a test block finishes."""

from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from typing import ParamSpec


P = ParamSpec("P")


class SoftAssertionError(AssertionError):
    """Aggregated failure with access to each original assertion error."""

    def __init__(self, failures: Sequence[AssertionError]) -> None:
        self.failures = tuple(failures)
        details = "\n\n".join(
            f"{number}. {error}" for number, error in enumerate(self.failures, 1)
        )
        super().__init__(f"{len(self.failures)} soft assertion(s) failed:\n{details}")


class _SoftAssertions:
    def __init__(self) -> None:
        self._failures: list[AssertionError] = []

    def check(self, assertion: Callable[P, None], *args: P.args, **kwargs: P.kwargs) -> None:
        """Run one assertion and record its failure while allowing later checks."""
        try:
            assertion(*args, **kwargs)
        except AssertionError as error:
            self._failures.append(error)

    def _raise_if_failed(self) -> None:
        if self._failures:
            raise SoftAssertionError(self._failures)


@contextmanager
def soft_assertions() -> Iterator[_SoftAssertions]:
    """Collect check() failures and report them together when the block exits.

    Unexpected exceptions leave the block immediately and retain their type.
    """
    collector = _SoftAssertions()
    yield collector
    collector._raise_if_failed()
