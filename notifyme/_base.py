from __future__ import annotations

import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import ContextDecorator
from datetime import datetime
from types import TracebackType
from typing import Any, Self, Type

import notifyme._log as _log
from notifyme._utils import format_timedelta


class _BaseNotifier(ABC):
    platform: str

    def __init__(self, verbose: bool = True) -> None:
        self._verbose = verbose

    def send(self, data: Any, **kwargs: Any) -> None:
        if self._verbose:
            _log.info(f"Send message: {data}")
        self._send(data, **kwargs)

    def _send(self, data: Any, **kwargs: Any) -> None:
        try:
            self._do_send(data, **kwargs)
        except Exception as e:
            _log.info(f"Error sending to {self.platform}: {e}")

    @abstractmethod
    def _do_send(self, data: Any) -> None:
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
        if self._verbose:
            log(message)
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
        et_msg = f"Execution time: {format_timedelta(end - self._start)}"
        if exc_type:
            tb_str = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            error_msg = f"Error while watching{self._details}: {exc_val}\n{et_msg}"
            if self._verbose:
                _log.error(error_msg)
            self._send(f"{error_msg}\n{'-' * 40}\n{tb_str}")
        else:
            msg = f"Stop watching{self._details}.\n{et_msg}."
            if self._verbose:
                _log.info(msg)
            self._send(msg)

    @property
    def _details(self) -> str:
        details = ", ".join(
            filter(None, [self._label, self._fn_name and f"function: {self._fn_name}"])
        )
        return f" [{details}]" if details else ""

    def __call__(self, fn: Callable) -> Any:
        self._fn_name = fn.__name__
        return super().__call__(fn)
