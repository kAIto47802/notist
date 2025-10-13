from __future__ import annotations

import inspect
import linecache
import traceback
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, ContextDecorator
from datetime import datetime
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from notist._log import (
    LEVEL_ORDER,
    RESET,
    LevelStr,
    fg256,
)
from notist._log import Glyph as _G
from notist._log import SpecialToken as _S
from notist._utils import format_timedelta

if TYPE_CHECKING:
    import sys
    from collections.abc import Generator, Iterable
    from types import TracebackType

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
T = TypeVar("T")
_F = TypeVar("_F", bound=Callable[..., Any])


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
        self._defined_at: str | None = None
        self._is_fn = False
        self._filename: str | None = None
        self._lineno: int | None = None
        self._combined: bool = False

    def __enter__(self) -> Self:
        self._start = datetime.now()

        f = (f0 := inspect.currentframe()) and f0.f_back
        if self._is_fn:
            f = f and f.f_back
        if self._combined:
            f = f and f.f_back

        self._filename = f and f.f_code.co_filename
        fnname = f and f.f_code.co_name
        self._lineno = f and f.f_lineno
        module = f and f.f_globals.get("__name__", "<unknown>")

        module_fname = (
            f"{_S.BT_ALW}{module}.{fnname}{_S.BT_ALW}"
            if fnname != "<module>"
            else f"{_S.BT_ALW}{module}{_S.BT_ALW}"
        )
        if self._is_fn:
            self._called_from = f"{module_fname} @ {self._filename}:{self._lineno}"
        else:
            self._called_from = f"{self._filename}:{self._lineno}"
            self._target = f"code block in {module_fname}"

        message = f"Start watching{self._details()}"
        self._send(message)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._start
        end = datetime.now()
        et_msg_raw = f"Execution time: {format_timedelta(end - self._start)}"
        et_msg = fg256(8) + " " + _G.CBULLET + " " + et_msg_raw + RESET
        exc_only = "".join(traceback.format_exception_only(exc_type, exc_val)).strip()
        if exc_type:
            tb_str = "".join(traceback.format_exception(exc_type, exc_val, tb))
            error_msg = (
                f"Error while watching{self._details('error', exc_only)}\n{et_msg}"
            )
            self._send(error_msg, tb=tb_str, level="error")
        else:
            msg = f"End watching{self._details()}\n{et_msg}"
            self._send(msg)

    def _details(self, level: LevelStr = "info", message: str | None = None) -> str:
        assert self._called_from is not None
        target = (
            f" {fg256(45)}<{self._target}> [label: {self._label}]{RESET}"
            if self._label
            else f" {fg256(45)}<{self._target}>{RESET}"
        )
        called_lines = (
            (LEVEL_ORDER[self._callsite_level] <= LEVEL_ORDER[level])
            and _get_called_lines_str(
                self._filename,
                self._lineno,
                self._callsite_context_before,
                self._callsite_context_after,
                message,
            )
            or None
        )
        if self._is_fn:
            assert self._defined_at is not None
            defined_at = f" {fg256(8)}{_G.RARROWF} Defined at: {fg256(12)}{self._defined_at}{RESET}"
            called_from = f" {fg256(8)}{_G.RARROWF} Called from: {fg256(12)}{self._called_from}{RESET}"
            return "\n".join(
                filter(None, [target, defined_at, called_from, called_lines])
            )
        else:
            called_from = (
                f" {fg256(8)}{_G.RARROWF} at: {fg256(12)}{self._called_from}{RESET}"
            )
            return "\n".join(filter(None, [target, called_from, called_lines]))

    def __call__(self, fn: _F) -> _F:
        self._is_fn = True
        filename = inspect.getsourcefile(fn) or fn.__code__.co_filename
        lineno = fn.__code__.co_firstlineno
        module = fn.__module__
        qualname = fn.__qualname__
        self._target = f"function {_S.BT_ALW}{module}.{qualname}{_S.BT_ALW}"
        self._defined_at = f"{filename}:{lineno}"

        return super().__call__(fn)


class IterableWatch(AbstractContextManager, Generic[T]):
    def __init__(
        self,
        iterable: Iterable[T],
        step: int,
        total: int | None,
        send_fn: Callable[..., None],
        label: str | None,
        callsite_level: LevelStr = "error",
        callsite_context_before: int = 1,
        callsite_context_after: int = 4,
        class_name: str | None = None,
        object_id: int | None = None,
    ) -> None:
        self._iterable = iterable
        self._step = step
        self._total = (
            len_fn() if (len_fn := getattr(iterable, "__len__", None)) else total
        )
        self._send = send_fn
        self._label = label
        self._callsite_level = callsite_level
        self._callsite_context_before = callsite_context_before
        self._callsite_context_after = callsite_context_after
        self._iterable_object_str = f"{class_name or iterable.__class__.__name__} object at {object_id or hex(id(iterable))}"
        self._start: datetime | None = datetime.now()
        self._count: int | None = None
        self._prev_start: datetime | None = None
        self._cur_range_start: int | None = None
        self._cur_range_end: int | None = None
        self._filename: str | None = None
        self._lineno: int | None = None
        self._called_from: str | None = None
        self._combined: bool = False
        self._is_context = False

    def __enter__(self) -> Self:
        self._is_context = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        assert self._count is not None
        if not exc_type:
            return
        tb_str = "".join(traceback.format_exception(exc_type, exc_val, tb))
        exc_only = "".join(traceback.format_exception_only(exc_type, exc_val)).strip()
        message = (
            "Error while processing "
            + self._item_message
            + (f"of {self._total} " if self._total is not None else "")
            + "from"
            + self._details("error", exc_only)
            + "\n"
            + self._et_message
        )
        self._send(message, tb=tb_str, level="error")

    def __iter__(self) -> Iterator[T]:
        return self._gen()

    def _gen(self) -> Generator[T, None, None]:
        self._on_iter_start()
        for item in self._iterable:
            self._on_step_start()
            yield item
            self._on_step_end()
        self._on_iter_end()

    def _send_end_message(self) -> None:
        self._send(
            "Processed "
            + self._item_message
            + (f"of {self._total} " if self._total is not None else "")
            + f"from{self._details()}\n"
            + self._et_message
        )

    def _on_iter_start(self) -> None:
        self._set_callsite_info()
        self._start = datetime.now()
        self._send(f"Start watching{self._details()}")

    def _on_iter_end(self) -> None:
        assert self._count is not None
        if (self._count + 1) % self._step:
            self._cur_range_end = self._count + 1
            self._send_end_message()

        assert self._start is not None
        end = datetime.now()
        self._send(
            f"End watching{self._details()}\n"
            f"{fg256(8)} {_G.CBULLET} "
            f"Total execution time: {format_timedelta(end - self._start)}"
        )

    def _on_step_start(self) -> None:
        self._count = 0 if self._count is None else self._count + 1
        assert self._count is not None
        if self._count % self._step:
            return
        self._cur_range_start = self._count + 1
        self._cur_range_end = min(self._count + self._step, self._total or 1 << 30)
        self._prev_start = datetime.now()
        self._send(
            "Processing "
            + self._item_message
            + (f"of {self._total} " if self._total is not None else "")
            + f"from{self._details()}"
        )

    def _on_step_end(self) -> None:
        if self._count is None or (self._count + 1) % self._step:
            return
        self._send_end_message()

    def _set_callsite_info(self) -> None:
        f = (f0 := inspect.currentframe()) and (f1 := f0.f_back) and f1.f_back
        if not self._is_context:
            f = f and f.f_back
        if self._combined:
            f = f and f.f_back
        self._filename = f and f.f_code.co_filename
        fnname = f and f.f_code.co_name
        self._lineno = f and f.f_lineno
        module = f and f.f_globals.get("__name__", "<unknown>")
        module_fname = f"{module}.{fnname}" if fnname != "<module>" else f"{module}"
        self._called_from = (
            f"{_S.BT_ALW}{module_fname}{_S.BT_ALW} @ {self._filename}:{self._lineno}"
        )

    def _details(self, level: LevelStr = "info", message: str | None = None) -> str:
        target = (
            f" {fg256(45)}{_S.BT_MSG}<{self._iterable_object_str}>{_S.BT_MSG} [label: {self._label}]{RESET}"
            if self._label
            else f" {fg256(45)}{_S.BT_MSG}<{self._iterable_object_str}>{_S.BT_MSG}{RESET}"
        )
        called_from = (
            f" {fg256(8)}{_G.RARROWF} in: {fg256(12)}{self._called_from}{RESET}"
        )
        called_lines = (
            (LEVEL_ORDER[self._callsite_level] <= LEVEL_ORDER[level])
            and _get_called_lines_str(
                self._filename,
                self._lineno,
                self._callsite_context_before,
                self._callsite_context_after,
                message,
            )
            or None
        )
        return "\n".join(filter(None, [target, called_from, called_lines]))

    @property
    def _et_message(self) -> str:
        end = datetime.now()
        assert self._prev_start is not None
        assert self._start is not None
        return (
            f"{fg256(8)} {_G.CBULLET} Execution time for "
            + self._item_message.rstrip()
            + (f" of {self._total}" if self._total is not None else "")
            + f": {format_timedelta(end - self._prev_start)}{RESET}\n"
            + f"{fg256(8)} {_G.CBULLET}"
            + f" Total execution time: {format_timedelta(end - self._start)}{RESET}"
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


def _get_called_lines_str(
    filename: str | None,
    lineno: int | None,
    callsite_context_before: int,
    callsite_context_after: int,
    message: str | None = None,
) -> str | None:
    if not filename or lineno is None:
        return None
    called_lines = [
        (num := lineno + i, linecache.getline(filename, num).rstrip())
        for i in range(-callsite_context_before, callsite_context_after)
    ]
    w = len(str(called_lines[-1][0]))
    called_lines_ls = [
        f"  {fg256(20)}{i:>{w}d} {fg256(57)}{_G.V}{RESET} {line}"
        for i, line in called_lines
    ]
    wnum = len(line := called_lines[callsite_context_before][1]) - (
        snum := len(line.lstrip())
    )
    underline = (
        fg256(45) + _G.TL + _G.H * (3 + wnum) + _G.TDH * 2 + " " + _G.H * snum + RESET
        if message
        else fg256(45) + " " * 7 + " " * wnum + _G.H * snum + RESET
    )
    return (
        _S.FNO_MSG
        + "\n".join(
            called_lines_ls[: (idx := callsite_context_before + 1)]
            + [underline]
            + [
                f"{fg256(45)}{_G.V}{RESET}{line[1:]}" if message else line
                for line in called_lines_ls[idx:]
            ]
            + (
                [
                    f"{fg256(45)}{_G.BL}{_G.H}{_G.RARROWP}{RESET} {fg256(197)}{message}{RESET}"
                ]
                if message
                else []
            )
        )
        + _S.FNC_MSG
    )
