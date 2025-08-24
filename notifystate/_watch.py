from __future__ import annotations

import functools
import inspect
import linecache
import sys
import traceback
from collections.abc import Callable
from contextlib import AbstractContextManager, ContextDecorator
from datetime import datetime
from types import TracebackType
from typing import Any, Protocol, Type, TypeVar

from notifystate._log import (
    _BL,
    _CBULLET,
    _H,
    _RARROWF,
    _RARROWP,
    _RESET,
    _TDH,
    _TL,
    _V,
    LEVEL_ORDER,
    LevelStr,
    fg256,
)
from notifystate._utils import format_timedelta

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
P = ParamSpec("P")
R = TypeVar("R")


# This protocol guarantees to static checkers (e.g. mypy) that any implementing
# object have  `__enter__`, `__exit__` and `__call__`.
# Otherwise, users applying these contexts would get mypy errors because the type
# system wouldn't know these methods exist.
class ContextManagerDecorator(Protocol[P, R]):
    """Protocol for objects that can be used as context managers and decorators."""

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...
    def __call__(self, fn: Callable[P, R]) -> Callable[P, R]: ...


class Watch(ContextDecorator, AbstractContextManager):
    def __init__(
        self,
        send_fn: Callable[..., None],
        label: str | None = None,
        callsite_level: LevelStr = "error",
        callsite_context_before: int = 1,
        callsite_context_after: int = 4,
    ) -> None:
        self._send = send_fn
        self._start: datetime | None = None
        self._label = label
        self._callsite_level = callsite_level
        self._callsite_context_before = callsite_context_before
        self._callsite_context_after = callsite_context_after
        self._target: str | None = None
        self._called_from: str | None = None
        self._called_lines: list[tuple[int, str]] | None = None
        self._defined_at: str | None = None
        self._is_fn = False

    def __enter__(self) -> Self:
        self._start = datetime.now()

        f = (
            ((f0 := inspect.currentframe()) and (f1 := f0.f_back) and f1.f_back)
            if self._is_fn
            else (f0 := inspect.currentframe()) and f0.f_back
        )
        filename = f and f.f_code.co_filename
        fnname = f and f.f_code.co_name
        lineno = f and f.f_lineno
        module = f and f.f_globals.get("__name__", "<unknown>")
        self._called_lines = (
            [
                (num := lineno + i, linecache.getline(filename, num).rstrip())
                for i in range(
                    -self._callsite_context_before, self._callsite_context_after
                )
            ]
            if filename and lineno is not None
            else None
        )
        module_fname = f"`{module}.{fnname}`" if fnname != "<module>" else f"`{module}`"
        if self._is_fn:
            self._called_from = f"{module_fname} @ {filename}:{lineno}"
        else:
            self._called_from = f"{filename}:{lineno}"
            self._target = f"code block in {module_fname}"

        message = f"Start watching{self._details()}"
        self._send(message)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._start
        end = datetime.now()
        et_msg_raw = f"Execution time: {format_timedelta(end - self._start)}"
        et_msg = fg256(8) + " " + _CBULLET + " " + et_msg_raw + _RESET
        exc_only = "".join(traceback.format_exception_only(exc_type, exc_val)).strip()
        if exc_type:
            tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            error_msg = (
                f"Error while watching{self._details('error')}\n"
                + (fg256(45) + _BL + _H + _RARROWP + _RESET + " ")
                + (fg256(197) + exc_only + _RESET + "\n")
                + et_msg
            )
            self._send(error_msg, tb=tb, level="error")
        else:
            msg = f"End watching{self._details()}\n{et_msg}"
            self._send(msg)

    def _details(self, level: LevelStr = "info") -> str:
        assert self._called_from is not None
        target = (
            f" {fg256(45)}<{self._target}> [label: {self._label}]{_RESET}"
            if self._label
            else f" {fg256(45)}<{self._target}>{_RESET}"
        )
        called_lines = (
            LEVEL_ORDER[self._callsite_level] <= LEVEL_ORDER[level]
        ) and self._get_called_lines_str(level == "error")
        if self._is_fn:
            assert self._defined_at is not None
            defined_at = f" {fg256(8)}{_RARROWF} Defined at: {fg256(12)}{self._defined_at}{_RESET}"
            called_from = f" {fg256(8)}{_RARROWF} Called from: {fg256(12)}{self._called_from}{_RESET}"
            return "\n".join(
                filter(None, [target, defined_at, called_from, called_lines])
            )
        else:
            called_from = (
                f" {fg256(8)}{_RARROWF} at: {fg256(12)}{self._called_from}{_RESET}"
            )
            return "\n".join(filter(None, [target, called_from, called_lines]))

    def _get_called_lines_str(self, with_arrow: bool) -> str | None:
        if not self._called_lines:
            return None
        w = len(str(self._called_lines[-1][0]))
        called_lines_ls = [
            f"  {fg256(20)}{i:>{w}d} {fg256(57)}{_V}{_RESET} {line}"
            for i, line in self._called_lines
        ]
        wnum = len(line := self._called_lines[self._callsite_context_before][1]) - (
            snum := len(line.lstrip())
        )
        underline = (
            fg256(45) + _TL + _H * (3 + wnum) + _TDH * 2 + " " + _H * snum + _RESET
            if with_arrow
            else fg256(45) + " " * 7 + " " * wnum + _H * snum + _RESET
        )
        return "\n".join(
            called_lines_ls[: (idx := self._callsite_context_before + 1)]
            + [underline]
            + [
                fg256(45) + _V + _RESET + l[1:] if with_arrow else l
                for l in called_lines_ls[idx:]
            ]
        )

    def __call__(self, fn: Callable) -> Any:
        self._is_fn = True
        filename = inspect.getsourcefile(fn) or fn.__code__.co_filename
        lineno = fn.__code__.co_firstlineno
        module = fn.__module__
        qualname = fn.__qualname__
        self._target = f"function `{module}.{qualname}`"
        self._defined_at = f"{filename}:{lineno}"

        wrapped = super().__call__(fn)
        return functools.wraps(fn)(wrapped)


class IterableWatch(AbstractContextManager):
    def __init__(
        self,
        step: int,
        total: int | None,
        details: str,
        start: datetime,
        send_fn: Callable[..., None],
    ) -> None:
        self._step = step
        self._total = total
        self._details = details
        self._start = start
        self._count: int | None = None
        self._prev_start: datetime | None = None
        self._send = send_fn
        self._cur_range_start: int | None = None
        self._cur_range_end: int | None = None

    def __enter__(self) -> Self:
        self._count = 0 if self._count is None else self._count + 1
        assert self._count is not None
        if self._count % self._step:
            return self
        self._cur_range_start = self._count + 1
        self._cur_range_end = min(self._count + self._step, self._total or 1 << 30)
        self._prev_start = datetime.now()
        message = (
            "Processing "
            + self._item_message
            + (f"of {self._total} " if self._total is not None else "")
            + f"from{self._details}..."
        )
        self._send(message)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._count is not None
        if exc_type:
            message = (
                "Error while processing "
                + self._item_message
                + (f"of {self._total} " if self._total is not None else "")
                + f"from{self._details}\n"
                + self._et_message
            )
            self._send(message, level="error")
            return
        if (self._count + 1) % self._step:
            return
        self._send_end_message()

    def _send_end_message(self) -> None:
        message = (
            "Processed "
            + self._item_message
            + (f"of {self._total} " if self._total is not None else "")
            + f"from{self._details}.\n"
            + self._et_message
        )
        self._send(message)

    def send_final_message_if_needed(self) -> None:
        assert self._count is not None
        if not (self._count + 1) % self._step:
            return
        self._cur_range_end = self._count + 1
        self._send_end_message()

    @property
    def _et_message(self) -> str:
        end = datetime.now()
        assert self._prev_start is not None
        return (
            "Execution time for "
            + self._item_message.rstrip()
            + (f" of {self._total}" if self._total is not None else "")
            + f": {format_timedelta(end - self._prev_start)}.\n"
            + f"Total execution time: {format_timedelta(end - self._start)}."
        )

    @property
    def _item_message(self) -> str:
        assert self._cur_range_start is not None
        assert self._cur_range_end is not None
        return (
            f"item {self._cur_range_start} "
            if self._step == 1
            else f"items {self._cur_range_start}–{self._cur_range_end} "
        )
