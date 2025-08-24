from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, TypeVar

import notifystate._log as _log
from notifystate._log import Glyph as _G
from notifystate._log import LevelStr, fg256, prepare_for_message
from notifystate._utils import format_timedelta
from notifystate._watch import ContextManagerDecorator, IterableWatch, Watch

if TYPE_CHECKING:
    from collections.abc import Iterable
    from types import ModuleType
    from typing import Any


@dataclass
class SendConfig:
    channel: str | None = None
    mention_to: str | None = None
    mention_level: LevelStr = "error"
    mention_if_ends: bool = True
    verbose: bool = True
    disable: bool = False


DOC_ADDITIONS_BASE = {
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
        mention_level: LevelStr = "error",
        mention_if_ends: bool = True,
        callsite_level: LevelStr = "error",
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
            mention_level: Minimum log level to trigger a mention.
            mention_if_ends: Whether to mention at the end of the watch.
            callsite_level: Minimum log level to emit the call-site source snippet.
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
        self._default_callsite_level = callsite_level
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
            str(data),
            SendConfig(
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
        data: str,
        send_config: SendConfig,
        tb: str | None = None,
        level: LevelStr = "info",
        prefix: str = "",
    ) -> None:
        try:
            if not send_config.disable:
                self._do_send(prepare_for_message(data), send_config, tb, level)
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
        data: str,
        send_config: SendConfig,
        tb: str | None = None,
        level: LevelStr = "info",
    ) -> None:
        raise NotImplementedError

    def watch(
        self,
        label: str | None = None,
        *,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: LevelStr | None = None,
        mention_if_ends: bool | None = None,
        callsite_level: LevelStr | None = None,
        callsite_context_before: int = 1,
        callsite_context_after: int = 4,
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
            callsite_level: Override the default call-site source snippet threshold level.
            callsite_context_before: Number of lines of context to include before the call site.
            callsite_context_after: Number of lines of context to include after the call site.
            verbose: Override the default verbosity setting.
            disable: Override the default disable flag.

        Returns:
            An an object that can serve as both a context manager and a decorator.
        """
        send_config = SendConfig(
            channel=channel or self._default_channel,
            mention_to=mention_to or self._mention_to,
            mention_level=mention_level or self._mention_level,
            mention_if_ends=mention_if_ends
            if mention_if_ends is not None
            else self._mention_if_ends,
            verbose=verbose if verbose is not None else self._verbose,
            disable=disable if disable is not None else self._disable,
        )
        return Watch(
            partial(self._send, send_config=send_config),
            label,
            callsite_level or self._default_callsite_level,
            callsite_context_before,
            callsite_context_after,
        )

    def register(
        self,
        target: ModuleType | type[Any] | Any,
        name: str,
        *,
        label: str | None = None,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: LevelStr | None = None,
        mention_if_ends: bool | None = None,
        callsite_level: LevelStr | None = None,
        callsite_context_before: int = 1,
        callsite_context_after: int = 4,
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
            callsite_level: Override the default call-site source snippet threshold level.
            callsite_context_before: Number of lines of context to include before the call site.
            callsite_context_after: Number of lines of context to include after the call site.
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
            callsite_level=callsite_level,
            callsite_context_before=callsite_context_before,
            callsite_context_after=callsite_context_after,
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
        mention_level: LevelStr | None = None,
        mention_if_ends: bool | None = None,
        callsite_level: LevelStr | None = None,
        callsite_context_before: int = 1,
        callsite_context_after: int = 4,
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
        iterable_object = f"{iterable.__class__.__name__} object at {hex(id(iterable))}"
        send_config = SendConfig(
            channel=channel or self._default_channel,
            mention_to=mention_to or self._mention_to,
            mention_level=mention_level or self._mention_level,
            mention_if_ends=mention_if_ends
            if mention_if_ends is not None
            else self._mention_if_ends,
            verbose=verbose if verbose is not None else self._verbose,
            disable=disable if disable is not None else self._disable,
        )
        if step < 1:
            step = 1
            _log.warn(
                f"Step must be at least 1. Setting step to 1 for {self._platform}Notifier."
            )

        iterable_watch = IterableWatch(
            step,
            total,
            iterable_object,
            start,
            partial(self._send, send_config=send_config),
            label,
            callsite_level or self._default_callsite_level,
            callsite_context_before,
            callsite_context_after,
        )

        message = f"Start watching{iterable_watch.details()}"
        self._send(message, send_config)

        for item in iterable:
            with iterable_watch:
                yield item
        iterable_watch.send_final_message_if_needed()

        end = datetime.now()
        message = (
            f"End watching{iterable_watch.details()}\n"
            f"{fg256(8)} {_G.CBULLET} "
            f"Total execution time: {format_timedelta(end - start)}"
        )
        self._send(message, send_config)
