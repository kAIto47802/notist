from __future__ import annotations

import functools
import inspect
import linecache
import os
import sys
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from contextlib import AbstractContextManager, ContextDecorator
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from types import FrameType, ModuleType, TracebackType
from typing import Any, Literal, Protocol, Type, TypeVar, cast

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import notifystate._log as _log
from notifystate._utils import format_timedelta

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


_DOC_ADDITIONS_BASE = {
    "send": lambda cls: f"""
        Example:

            .. code-block:: python

               # Immediately send "Job finished!" to your Slack channel
               {cls._platform.lower()}.send("Job finished!")

               # You can also send any Python data (it will be stringified)
               {cls._platform.lower()}.send(data)
        """,
    "watch": lambda cls: f"""
        Example:

            .. code-block:: python

               # Use as a decorator to monitor a function
               @{cls._platform.lower()}.watch()
               def my_function():
                   # This function will be monitored
                   # Your long-running code here
                   ...

               # Or use as a context manager to monitor a block of code
               with {cls._platform.lower()}.watch():
                   # Code inside this block will be monitored
                   # Your long-running code here
                   ...
        """,
    "register": lambda cls: f"""
        Example:

            If you want to monitor existing functions from libraries:

            .. code-block:: python

               import requests

               # Register the `get` function from the `requests` library
               {cls._platform.lower()}.register(requests, "get")

               # Now any time you call `requests.get`, it will be monitored
               response = requests.get("https://example.com/largefile.zip")

            If you want to monitor existing methods of classes:

            .. code-block:: python

               from transformers import Trainer

               # Register the `train` method of the `Trainer` class
               {cls._platform.lower()}.register(Trainer, "train")

               # Now any time you call `trainer.train()`, it will be monitored
               trainer = Trainer(model=...)
               trainer.train()

            If you want to monitor existing methods of specific class instances:

            .. code-block:: python

               from transformers import Trainer

               # Create a Trainer instance
               trainer = Trainer(model=...)

               # Register the `train` method of the `trainer` instance
               {cls._platform.lower()}.register(trainer, "train")

               # Now any time you call `trainer.train()`, it will be monitored
               trainer.train()
        """,
}

T = TypeVar("T")


class BaseNotifier(ABC):
    """
    Abstract base class for all notifiers.

    Provides common functionality for sending messages and watching
    code execution, with optional exception handling and verbosity.
    """

    _platform: str
    """Name of the notification platform (e.g., "Slack")."""

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
        """
        Initialize the notifier with default settings.
        This settings can be overridden at each call of :meth:`register`, :meth:`send`, and :meth:`watch`.

        Args:
            channel:
                Default channel for notifications. If not provided, it will look for an environment variable
                named `{platform}_CHANNEL` where `{platform}` is the notifier's platform name in uppercase
                (e.g., `SLACK_CHANNEL` for Slack).
            mention_to: Default entity to mention on notification.
            mention_level: Threshold level at or above which mentions are sent.
            mention_if_ends: Whether to mention at the end of the watch.
            token:
                API token or authentication key. If not provided, it will look for an environment variable named
                `{platform}_BOT_TOKEN` where `{platform}` is the notifier's platform name in uppercase
                (e.g., `SLACK_BOT_TOKEN` for Slack).
            verbose: If obj:`True`, log internal state changes.
            disable:
                If :obj:`True`, disable sending all notifications. This is useful for parallel runs or testing
                where you want to avoid sending actual notifications.

        .. note::
           The channel and token must be set, either via environment variables or as function arguments.
           If not set, the notification will not be sent, and an error will be logged
           (the original Python script will continue running without interruption).
        """
        self._verbose = verbose
        self._mention_to = mention_to or os.getenv(
            f"{self._platform.upper()}_MENTION_TO"
        )
        self._token = token or os.getenv(f"{self._platform.upper()}_BOT_TOKEN")
        if not self._token and self._verbose:
            _log.error(
                f"Missing {self._platform} bot token. Please set the {self._platform.upper()}_BOT_TOKEN "
                "environment variable or pass it as an argument."
            )
            self._disable = True
        self._mention_level = mention_level
        self._mention_if_ends = mention_if_ends
        self._default_channel = channel or os.getenv(
            f"{self._platform.upper()}_CHANNEL"
        )
        self._disable = disable
        if disable and self._verbose:
            _log.info(
                f"{self._platform}Notifier is disabled. No messages will be sent."
            )

    def send(
        self,
        data: Any,
        *,
        channel: str | None = None,
        mention_to: str | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> None:
        """
        Send a notification message.
        You can send notifications at any point in your code, not just at the start or end of a task.
        Any data can be sent, and it will be stringified.

        Args:
            data: The payload or message content.
            channel: Override the default channel for notifications.
            mention_to: Override the default entity to mention on notification.
            verbose: Override the default verbosity setting.
            disable: Override the default disable flag.
        """
        self._send(
            data,
            _SendConfig(
                channel=channel or self._default_channel,
                mention_to=mention_to or self._mention_to,
                mention_level="info" if mention_to or self._mention_to else "error",
                verbose=verbose if verbose is not None else self._verbose,
                disable=disable if disable is not None else self._disable,
            ),
            prefix="Send message: ",
        )

    def _send(
        self,
        data: Any,
        send_config: _SendConfig,
        tb: str | None = None,
        level: _LevelStr = "info",
        prefix: str = "",
    ) -> None:
        try:
            if not send_config.disable:
                self._do_send(data, send_config, tb, level)
            if self._verbose:
                {
                    "info": _log.info,
                    "warning": _log.warn,
                    "error": _log.error,
                }[level](f"{prefix}{data}")
        except Exception as e:
            if self._verbose:
                _log.error(f"Error sending to {self._platform}: {e}")

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
        """
        Return an object that can serve as both a context manager and a decorator to watch code execution.
        This will automatically send notifications when the function or code block starts, ends, or raises an exception.

        Args:
            label: Optional label for the watch context. This label will be included in both notification messages and log entries.
            channel: Override the default channel for notifications.
            mention_to: Override the default entity to mention on notification.
            mention_level: Override the default mention threshold level.
            mention_if_ends: Override the default setting for whether to mention at the end of the watch.
            verbose: Override the default verbosity setting.
            disable: Override the default disable flag.

        Returns:
            An an object that can serve as both a context manager and a decorator.
        """
        send_config = _SendConfig(
            channel=channel or self._default_channel,
            mention_to=mention_to or self._mention_to,
            mention_level=mention_level or self._mention_level,
            mention_if_ends=mention_if_ends
            if mention_if_ends is not None
            else self._mention_if_ends,
            verbose=verbose if verbose is not None else self._verbose,
            disable=disable if disable is not None else self._disable,
        )
        return _Watch(
            partial(self._send, send_config=send_config),
            label,
        )

    def register(
        self,
        target: ModuleType | Type[Any] | Any,
        name: str,
        *,
        label: str | None = None,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr | None = None,
        mention_if_ends: bool | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> None:
        """
        Register existing function or method to be monitored by this notifier.
        This function corresponds to applying the :meth:`watch` decorator to an existing function or method.

        Args:
            target: The module, class, or class instance containing the function to be registered.
            name: The name of the function to be registered.
            label: Optional label for the watch context. This label will be included in both notification messages and log entries.
            channel: Override the default channel for notifications.
            mention_to: Override the default entity to mention on notification.
            mention_level: Override the default mention threshold level.
            mention_if_ends: Override the default setting for whether to mention at the end of the watch.
            verbose: Override the default verbosity setting.
            disable: Override the default disable flag.
        """
        original = getattr(target, name, None)
        if original is None:
            if verbose if verbose is not None else self._verbose:
                _log.warn(
                    f"Cannot register {self._platform}Notifier on `{target.__name__}.{name}`: "
                    f"target `{target.__name__}` has no attribute `{name}`."
                )
            return
        patched = self.watch(
            label=label,
            channel=channel,
            mention_to=mention_to,
            mention_level=mention_level,
            mention_if_ends=mention_if_ends,
            verbose=verbose,
            disable=disable,
        )(original)
        setattr(target, name, patched)
        target_name = (
            target.__name__
            if hasattr(target, "__name__")
            else f"<{target.__class__.__name__} object at {hex(id(target))}>"
        )
        if verbose if verbose is not None else self._verbose:
            _log.info(f"Registered {self._platform}Notifier on `{target_name}.{name}`.")

    def watch_iterable(
        self,
        iterable: Iterable[T],
        step: int = 1,
        total: int | None = None,
        *,
        label: str | None = None,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr | None = None,
        mention_if_ends: bool | None = None,
        verbose: bool | None = None,
        disable: bool | None = None,
    ) -> Iterable[T]:
        """
        A generator that yields items from an iterable while sending notifications about the progress.
        This is useful for monitoring long-running tasks that process items from an iterable.

        Args:
            iterable: The iterable to watch.
            step: The number of items to process before sending a progress notification.
            total: The total number of items in the iterable. If not provided, it will not be included in the progress messages.
            label: Optional label for the watch context. This label will be included in both notification messages and log entries.
            mention_to: Override the default entity to mention on notification.
            mention_level: Override the default mention threshold level.
            mention_if_ends: Override the default setting for whether to mention at the end of the watch.
            verbose: Override the default verbosity setting.
            disable: Override the default disable flag.
        """
        start = datetime.now()
        iterable_object = (
            f"<{iterable.__class__.__name__} object at {hex(id(iterable))}>"
        )
        send_config = _SendConfig(
            channel=channel or self._default_channel,
            mention_to=mention_to or self._mention_to,
            mention_level=mention_level or self._mention_level,
            mention_if_ends=mention_if_ends
            if mention_if_ends is not None
            else self._mention_if_ends,
            verbose=verbose if verbose is not None else self._verbose,
            disable=disable if disable is not None else self._disable,
        )
        details = f" {iterable_object} [{label}]" if label else f" {iterable_object}"
        message = f"Start watching{details}..."
        self._send(message, send_config)

        if step < 1:
            step = 1
            _log.warn(
                f"Step must be at least 1. Setting step to 1 for {self._platform}Notifier."
            )

        iterable_watch = _IterableWatch(
            step,
            total,
            details,
            start,
            partial(self._send, send_config=send_config),
        )

        for item in iterable:
            with iterable_watch:
                yield item
        iterable_watch.send_final_message_if_needed()

        end = datetime.now()
        message = (
            f"End watching{details}.\n"
            f"Total execution time: {format_timedelta(end - start)}."
        )
        self._send(message, send_config)


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
        label: str | None = None,
    ) -> None:
        self._send = send_fn
        self._start: datetime | None = None
        self._label = label
        self._target: str | None = None

    def __enter__(self) -> Self:
        self._start = datetime.now()

        if not self._target:
            f = cast(FrameType, cast(FrameType, inspect.currentframe()).f_back)
            filename = f.f_code.co_filename
            fnname = f.f_code.co_name
            lineno = f.f_lineno
            line = linecache.getline(filename, lineno).rstrip()
            self._target = f"{filename}:{lineno} in {fnname} :: {line}"

        message = f"Start watching{self._details}..."
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
        exc_only = "".join(traceback.format_exception_only(exc_type, exc_val)).strip()
        if exc_type:
            tb = "".join(traceback.format_exception(exc_type, exc_val, exc_tb))
            error_msg = f"Error while watching{self._details}: {exc_only}\n{et_msg}."
            self._send(error_msg, tb=tb, level="error")
        else:
            msg = f"End watching{self._details}.\n{et_msg}."
            self._send(msg)

    @property
    def _details(self) -> str:
        return (
            f" <{self._target}> [{self._label}]"
            if self._label
            else f" <{self._target}>"
        )

    def __call__(self, fn: Callable) -> Any:
        filename = inspect.getsourcefile(fn) or fn.__code__.co_filename
        lineno = fn.__code__.co_firstlineno
        module = fn.__module__
        qualname = fn.__qualname__
        self._target = f"function `{module}.{qualname}` in {filename}:{lineno}"

        wrapped = super().__call__(fn)
        return functools.wraps(fn)(wrapped)


class _IterableWatch(AbstractContextManager):
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
