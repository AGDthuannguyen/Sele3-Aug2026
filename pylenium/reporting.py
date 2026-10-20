"""Reporter-independent test steps for public actions and assertions."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager, nullcontext
from contextvars import ContextVar, Token
from functools import wraps
from time import time_ns
from typing import Any, ParamSpec, TypeVar


P = ParamSpec("P")
R = TypeVar("R")


class StepRecorder:
    """Collect one tree of steps for a pytest test and an optional reporter."""

    def __init__(
        self, step_context: Callable[[str], AbstractContextManager[Any]] | None = None,
    ) -> None:
        self.steps: list[dict[str, Any]] = []
        self.step_context = step_context


_recorder: ContextVar[StepRecorder | None] = ContextVar("pylenium_step_recorder", default=None)
_parent: ContextVar[dict[str, Any] | None] = ContextVar("pylenium_step_parent", default=None)


def install_recorder(recorder: StepRecorder) -> Token[StepRecorder | None]:
    """Activate a recorder for one pytest test; return its reset token."""
    return _recorder.set(recorder)


def reset_recorder(token: Token[StepRecorder | None]) -> None:
    _recorder.reset(token)


def current_recorder() -> StepRecorder | None:
    return _recorder.get()


@contextmanager
def record_step(name: str) -> Iterator[None]:
    """Record an operation once, regardless of its internal polling or retries."""
    recorder = _recorder.get()
    if recorder is None:
        yield
        return

    event: dict[str, Any] = {
        "name": name,
        "status": "running",
        "start": time_ns() // 1_000_000,
        "steps": [],
    }
    parent = _parent.get()
    (parent["steps"] if parent is not None else recorder.steps).append(event)
    token = _parent.set(event)

    context = recorder.step_context(name) if recorder.step_context is not None else nullcontext()

    try:
        with context:
            yield
    except BaseException as error:
        event["status"] = "failed"
        event["error"] = f"{type(error).__name__}: {error}"
        raise
    else:
        event["status"] = "passed"
    finally:
        event["stop"] = time_ns() // 1_000_000
        _parent.reset(token)


def step(name: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Mark a reusable operation as one step; {page} names its owning class."""
    def decorate(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            title = name.replace("{page}", type(args[0]).__name__) if args else name
            with record_step(title):
                return function(*args, **kwargs)

        return wrapped

    return decorate
