from __future__ import annotations

import os
import sys
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import AbstractContextManager, ContextDecorator
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from types import TracebackType
from typing import Any, Literal, Protocol, Type, TypeVar

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import notifyend._log as _log
from notifyend._utils import format_timedelta

# NOTE: Python 3.12+ (PEP 695) supports type statement.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/library/typing.html#type-aliases
_LevelStr = Literal["info", "warning", "error"]
_LEVEL_ORDER: dict[_LevelStr, int] = {
    "info": 0,
    "warning": 1,
    "error": 2,
}


@dataclass
class _SendConfig:
    channel: str | None = None
    mention_to: str | None = None
    mention_level: _LevelStr = "error"
    mention_if_ends: bool = True
    verbose: bool = True
    disable: bool = False


class _BaseNotifier(ABC):
    platform: str

    def __init__(
        self,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr = "error",
        mention_if_ends: bool = True,
        token: str | None = None,
        verbose: bool = True,
        disable: bool = False,
    ) -> None:
        self._verbose = verbose
        self._mention_to = mention_to or os.getenv(
            f"{self.platform.upper()}_MENTION_TO"
        )
        self._token = token or os.getenv(f"{self.platform.upper()}_BOT_TOKEN")
        if not self._token and self._verbose:
            _log.error(
                f"Missing {self.platform} bot token. Please set the {self.platform.upper()}_BOT_TOKEN "
                "environment variable or pass it as an argument."
            )
            self._disable = True
        self._mention_level = mention_level
        self._mention_if_ends = mention_if_ends
        self._default_channel = channel or os.getenv(f"{self.platform.upper()}_CHANNEL")
        self._disable = disable
        if disable and self._verbose:
            _log.info(f"{self.platform}Notifier is disabled. No messages will be sent.")

    def send(
        self,
        data: Any,
        *,
        channel: str | None = None,
        mention_to: str | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> None:
        self._send(
            data,
            _SendConfig(
                channel=channel or self._default_channel,
                mention_to=mention_to or self._mention_to,
                mention_level="info" if mention_to is not None else "error",
                verbose=verbose if verbose is not None else self._verbose,
                disable=disable if disable is not None else self._disable,
            ),
        )
        if self._verbose:
            _log.info(f"Send message: {data}")

    def _send(
        self,
        data: Any,
        send_config: _SendConfig,
        tb: str | None = None,
        level: _LevelStr = "info",
    ) -> None:
        if send_config.disable:
            return
        try:
            self._do_send(data, send_config, tb, level)
        except Exception as e:
            if self._verbose:
                _log.error(f"Error sending to {self.platform}: {e}")

    @abstractmethod
    def _do_send(
        self,
        data: Any,
        send_config: _SendConfig,
        tb: str | None = None,
        level: _LevelStr = "info",
    ) -> None:
        raise NotImplementedError

    def watch(
        self,
        label: str | None = None,
        *,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr | None = None,
        mention_if_ends: bool | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> ContextManagerDecorator:
        return _Watch(
            self._send,
            _SendConfig(
                channel=channel or self._default_channel,
                mention_to=mention_to or self._mention_to,
                mention_level=mention_level or self._mention_level,
                mention_if_ends=mention_if_ends
                if mention_if_ends is not None
                else self._mention_if_ends,
                verbose=verbose if verbose is not None else self._verbose,
                disable=disable if disable is not None else self._disable,
            ),
            label,
        )


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


class _Watch(ContextDecorator, AbstractContextManager):
    def __init__(
        self,
        send_fn: Callable[..., None],
        send_config: _SendConfig,
        label: str | None = None,
    ) -> None:
        self._send = partial(send_fn, send_config=send_config)
        self._send_config = send_config
        self._start: datetime | None = None
        self._label = label
        self._fn_name: str | None = None

    def __enter__(self) -> Self:
        self._start = datetime.now()
        message = f"Start watching{self._details}..."
        self._send(message)
        if self._send_config.verbose:
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
            error_msg = f"Error while watching{self._details}: {exc_val}\n{et_msg}."
            self._send(error_msg, tb=tb, level="error")
            if self._send_config.verbose:
                _log.error(error_msg)
        else:
            msg = f"Stop watching{self._details}.\n{et_msg}."
            self._send(msg)
            if self._send_config.verbose:
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
