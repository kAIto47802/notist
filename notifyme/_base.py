from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import ContextDecorator
from datetime import datetime
from types import TracebackType
from typing import Any, Literal, Self, Type

import notifyme._log as _log
from notifyme._utils import format_timedelta

_LevelType = Literal["info", "warning", "error"]


class _BaseNotifier(ABC):
    platform: str

    def __init__(self, verbose: bool = True) -> None:
        self._verbose = verbose

    def send(self, data: Any, **kwargs: Any) -> None:
        self._send(data, **kwargs)
        if self._verbose:
            _log.info(f"Send message: {data}")

    def _send(
        self,
        data: Any,
        tb: str | None = None,
        level: _LevelType = "info",
        **kwargs: Any,
    ) -> None:
        try:
            self._do_send(data, tb, level, **kwargs)
        except Exception as e:
            _log.error(f"Error sending to {self.platform}: {e}")

    @abstractmethod
    def _do_send(
        self, data: Any, tb: str | None = None, level: _LevelType = "info"
    ) -> None:
        raise NotImplementedError

    def watch(self, label: str | None = None) -> _Watch:
        return _Watch(self._send, self._verbose, label)


class _Watch(ContextDecorator):
    def __init__(
        self,
        send_fn: Callable[..., None],
        verbose: bool = True,
        label: str | None = None,
    ) -> None:
        self._send = send_fn
        self._verbose = verbose
        self._start: datetime | None = None
        self._label = label
        self._fn_name: str | None = None

    def __enter__(self) -> Self:
        self._start = datetime.now()
        message = f"Start watching{self._details}..."
        self._send(message)
        if self._verbose:
            _log.info(message)
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self._start
        end = datetime.now()
        et_msg = f"Execution time: {format_timedelta(end - self._start)}"
        if exc_type:
            tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            error_msg = f"Error while watching{self._details}: {exc_val}\n{et_msg}"
            self._send(error_msg, tb=tb, level="error")
            if self._verbose:
                _log.error(error_msg)
        else:
            msg = f"Stop watching{self._details}.\n{et_msg}."
            self._send(msg)
            if self._verbose:
                _log.info(msg)

    @property
    def _details(self) -> str:
        details = ", ".join(
            filter(None, [self._label, self._fn_name and f"function: {self._fn_name}"])
        )
        return f" [{details}]" if details else ""

    def __call__(self, fn: Callable) -> Any:
        self._fn_name = fn.__name__
        return super().__call__(fn)
