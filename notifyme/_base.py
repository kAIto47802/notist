from __future__ import annotations

import os
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from contextlib import ContextDecorator
from dataclasses import asdict, dataclass
from datetime import datetime
from functools import partial
from types import TracebackType
from typing import Any, Literal, Self, Type

import notifyme._log as _log
from notifyme._utils import format_timedelta

_LevelStr = Literal["info", "warning", "error"]
_LEVEL_ORDER: dict[_LevelStr, int] = {
    "info": 0,
    "warning": 1,
    "error": 2,
}


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
        self._mention_level = mention_level
        self._mention_if_ends = mention_if_ends
        self._default_channel = channel or os.getenv(f"{self.platform.upper()}_CHANNEL")
        self._disable = disable
        if disable:
            _log.info(f"{self.platform}Notifier is disabled. No messages will be sent.")

    def send(
        self,
        data: Any,
        *,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr | None = None,
        mention_if_ends: bool | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> None:
        self._send(
            data,
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
        if send_config.disable if send_config.disable is not None else self._disable:
            return
        try:
            self._do_send(data, send_config, tb, level)
        except Exception as e:
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
    ) -> _Watch:
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


class _Watch(ContextDecorator):
    def __init__(
        self,
        send_fn: Callable[..., None],
        send_config: _SendConfig,
        label: str | None = None,
    ) -> None:
        self._send = partial(send_fn, **asdict(send_config))
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
            error_msg = f"Error while watching{self._details}: {exc_val}\n{et_msg}"
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


@dataclass
class _SendConfig:
    channel: str | None = None
    mention_to: str | None = None
    mention_level: _LevelStr = "error"
    mention_if_ends: bool = True
    verbose: bool = True
    disable: bool = False
