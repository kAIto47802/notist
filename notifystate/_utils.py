from __future__ import annotations

import functools
import textwrap
from collections.abc import Callable
from datetime import timedelta
from typing import Any, Type, TypeVar

T = TypeVar("T", bound=Type[Any])


def _clone_function(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Clone a function to avoid modifying the original."""

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return fn(*args, **kwargs)

    return wrapper


def extend_method_docstring(additions: dict[str, str]) -> Callable[[T], T]:
    """
    Class decorator factory that appends extra text to inherited methods' docstrings.

    `additions` should map method names (that aren't overridden) to the snippet you want appended.
    """

    def decorator(cls: T) -> T:
        for name, doc in additions.items():
            if not hasattr(cls, name):
                continue
            if name in cls.__dict__:
                raise ValueError(f"Method `{name}` is redefined in `{cls.__name__}`.")
            method = getattr(cls, name)
            base = method.__doc__ or ""
            extra = textwrap.dedent(doc).strip()
            new_doc = base + "\n\n" + textwrap.indent(extra, " " * 8)
            new_method = _clone_function(method)
            new_method.__doc__ = new_doc
            setattr(cls, name, new_method)
        return cls

    return decorator


def format_timedelta(td: timedelta) -> str:
    days = td.days
    hours, remainder = divmod(td.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    parts = [
        days and f"{days}d",
        hours and f"{hours}h",
        minutes and f"{minutes}m",
        seconds and f"{seconds}s",
    ]
    return " ".join([p for p in parts if p]) or "0s"
