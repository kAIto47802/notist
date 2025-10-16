from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, Protocol, TypedDict, TypeVar, overload

from notist import _log
from notist._log import LevelStr, prepare_for_message
from notist._watch import IterableWatch, Watch

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from types import ModuleType, TracebackType

    if sys.version_info >= (3, 12):
        from typing import Unpack
    else:
        from typing_extensions import Unpack


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
P = ParamSpec("P")
R = TypeVar("R")
T_co = TypeVar("T_co", covariant=True)
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Any])


# This protocol guarantees to static checkers (e.g. mypy) that any implementing
# object have  `__enter__`, `__exit__` and `__call__`.
# Otherwise, users applying these contexts would get mypy errors because the type
# system wouldn't know these methods exist.
class ContextManagerDecorator(Protocol[F]):
    """Protocol for objects that can be used as context managers and decorators."""

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
        /,
    ) -> None: ...
    def __call__(self, fn: F, /) -> F: ...


class ContextManagerIterator(Protocol[T_co]):
    """Protocol for objects that can be used as context managers and iterators."""

    def __enter__(self) -> Self: ...
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
        /,
    ) -> None: ...
    def __iter__(self) -> Iterator[T_co]: ...


@dataclass(frozen=True)
class _SendConfig:
    channel: str | None = None
    mention_to: str | None = None
    mention_level: LevelStr = "error"
    mention_if_ends: bool = True
    verbose: bool = True
    disable: bool = False


@dataclass(frozen=True)
class _SendFnPartial:
    fn: Callable[[_SendConfig, str, str | None, LevelStr, str], None]
    config: _SendConfig

    def __call__(
        self,
        message: str,
        tb: str | None = None,
        level: LevelStr = "info",
        prefix: str = "",
    ) -> None:
        self.fn(self.config, message, tb, level, prefix)


class SendOptions(TypedDict, total=False):
    """
    Additional options for :meth:`~BaseNotifier.watch` and :meth:`~BaseNotifier.register`.
    """

    #: Optional label for the message. Included in notification messages and log entries.
    label: str | None
    #: Override the default channel for notifications.
    channel: str | None
    #: Override the default user to mention on notification.
    mention_to: str | None
    #: Override the default mention threshold level.
    mention_level: LevelStr | None
    #: Override the default setting for whether to mention at the end of the watch.
    mention_if_ends: bool | None
    #: Override the default call-site source snippet threshold level.
    callsite_level: LevelStr | None
    #: Number of lines of context to include before the call site. Default is 1.
    callsite_context_before: int
    #: Number of lines of context to include after the call site. Default is 4.
    callsite_context_after: int
    #: Override the default verbosity setting.
    verbose: bool | None
    #: Override the default disable flag.
    disable: bool | None


@dataclass(frozen=True)
class _SendOptions:
    """
    Internal version of SendOptions with default values filled in.
    """

    label: str | None = None
    channel: str | None = None
    mention_to: str | None = None
    mention_level: LevelStr | None = None
    mention_if_ends: bool | None = None
    callsite_level: LevelStr | None = None
    callsite_context_before: int = 1
    callsite_context_after: int = 4
    verbose: bool | None = None
    disable: bool | None = None


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
    "watch_iterable": lambda cls: f"""
        Example:

            .. code-block:: python

                # Monitor progress of processing a long-running for loop
                for batch in {cls._platform.lower()}.watch_iterable(train_dataloader, step=10):
                    # This loop will be monitored, and you'll receive notifications every 10 iterations.
                    ...

        .. note::
           The above example does **not** catch exceptions automatically,
           since exceptions raised inside the for loop cannot be caught by the iterator in Python.
           If you also want to be notified when an error occurs, wrap your code in the monitoring context:

           .. code-block:: python

              with {cls._platform.lower()}.watch_iterable(train_dataloader, step=10) as it:
                  for batch in it:
                      # This loop will be monitored, and you'll receive notifications every 10 iterations.
                      # If an error occurs inside this context, you'll be notified immediately.
                      ...
        """,
}


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
        verbose: bool | int = True,
        disable: bool = False,
    ) -> None:
        """
        Initialize the notifier with default settings.
        This settings can be overridden at each call of :meth:`register`, :meth:`send`, and :meth:`watch`.

        Args:
            channel:
                Default channel for notifications. If not provided, it will look for an environment variable
                named ``{platform}_CHANNEL`` where ``{platform}`` is the notifier's platform name in uppercase
                (e.g., ``SLACK_CHANNEL`` for Slack).
            mention_to:
                Default user to mention in notification. If not provided, it will look for an environment variable
                named ``{platform}_MENTION_TO`` where ``{platform}`` is the notifier's platform name in uppercase
                (e.g., ``SLACK_MENTION_TO`` for Slack).
            mention_level: Minimum log level to trigger a mention.
            mention_if_ends: Whether to mention at the end of the watch.
            callsite_level: Minimum log level to emit the call-site source snippet.
            token:
                API token or authentication key. If not provided, it will look for an environment variable named
                ``{platform}_BOT_TOKEN`` where ``{platform}`` is the notifier's platform name in uppercase
                (e.g., ``SLACK_BOT_TOKEN`` for Slack).
            verbose:
                If obj:`True`, log messages to console.
                If set to 1, only logs during initialization.
                If set to 2 or higher, behaves the same as obj:`True`.
            disable:
                If :obj:`True`, disable sending all notifications. This is useful for parallel runs or testing
                where you want to avoid sending actual notifications.

        .. note::
           The channel and token must be set, either via environment variables or as function arguments.
           If not set, the notification will not be sent, and an error will be logged
           (the original Python script will continue running without interruption).
        """
        self._mention_to = mention_to or os.getenv(
            f"{self._platform.upper()}_MENTION_TO"
        )
        self._token = token or os.getenv(f"{self._platform.upper()}_BOT_TOKEN")
        if not self._token and verbose:
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
        if disable and verbose:
            _log.info(
                f"{self._platform}Notifier is disabled. No messages will be sent."
            )
        self._verbose = verbose if isinstance(verbose, bool) else verbose >= 2

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
            _SendConfig(
                channel=channel or self._default_channel,
                mention_to=mention_to or self._mention_to,
                mention_level="info" if mention_to or self._mention_to else "error",
                verbose=verbose if verbose is not None else self._verbose,
                disable=disable if disable is not None else self._disable,
            ),
            str(data),
            prefix="Send message: ",
        )

    def _send(
        self,
        send_config: _SendConfig,
        message: str,
        tb: str | None = None,
        level: LevelStr = "info",
        prefix: str = "",
    ) -> None:
        try:
            if not send_config.disable:
                self._do_send(send_config, prepare_for_message(message), tb, level)
            if send_config.verbose:
                {
                    "info": _log.info,
                    "warning": _log.warn,
                    "error": _log.error,
                }[level](f"{prefix}{message}")
        except Exception as e:
            if send_config.verbose:
                _log.error(f"Error sending to {self._platform}: {e}")

    @abstractmethod
    def _do_send(
        self,
        send_config: _SendConfig,
        message: str,
        tb: str | None = None,
        level: LevelStr = "info",
    ) -> None:
        raise NotImplementedError

    @overload
    def watch(
        self,
        iterable: None = ...,
        /,
        *,
        params: str | list[str] | None = ...,
        step: int = ...,
        total: None = ...,
        **kwargs: Unpack[SendOptions],
    ) -> ContextManagerDecorator: ...

    @overload
    def watch(
        self,
        iterable: Iterable[T],
        /,
        *,
        params: None = ...,
        step: int = ...,
        total: int | None = ...,
        **kwargs: Unpack[SendOptions],
    ) -> ContextManagerIterator[T]: ...

    def watch(
        self,
        iterable: Iterable[T] | None = None,
        /,
        *,
        params: str | list[str] | None = None,
        step: int = 1,
        total: int | None = None,
        **options: Unpack[SendOptions],
    ) -> ContextManagerDecorator | ContextManagerIterator[T]:
        """
        If ``iterable`` is not provided, return an object that can serve as both a context manager and
        a decorator to watch code execution.
        This will automatically send notifications when the function or code block starts, ends,
        or raises an exception.

        If ``iterable`` is provided, return a generator that yields items from an ``iterable``
        while sending notifications about its progress.

        Args:
            params:
                Names of the function parameters whose values should be included in the message
                when the decorated function is called.
                This option is ignored when used as a context manager.
            step:
                The number of items to process before sending a progress notification.
                This option is ignored if the iterable is not provided.
            total:
                The total number of items in the iterable.
                If not provided and the iterable has not ``__len__``,
                it will not be included in the progress messages.
                This option is ignored if the iterable is not provided.
            **options: Additional options. See :class:`SendOptions` for details.

        Returns:
            An an object that can serve as both a context manager and a decorator.
        """
        return self._watch_impl(
            iterable,
            params=params,
            step=step,
            total=total,
            **options,
        )

    def _watch_impl(
        self,
        iterable: Iterable[T] | None = None,
        /,
        *,
        params: str | list[str] | None = None,
        step: int = 1,
        total: int | None = None,
        combined: int = 0,
        class_name: str | None = None,
        object_id: int | None = None,
        **options: Unpack[SendOptions],
    ) -> Watch | IterableWatch[T]:
        opts = _SendOptions(**options)
        send_config = _SendConfig(
            channel=opts.channel or self._default_channel,
            mention_to=opts.mention_to or self._mention_to,
            mention_level=opts.mention_level or self._mention_level,
            mention_if_ends=opts.mention_if_ends
            if opts.mention_if_ends is not None
            else self._mention_if_ends,
            verbose=opts.verbose if opts.verbose is not None else self._verbose,
            disable=opts.disable if opts.disable is not None else self._disable,
        )
        if iterable is None:
            return Watch(
                _SendFnPartial(self._send, send_config),
                params,
                opts.label,
                opts.callsite_level or self._default_callsite_level,
                opts.callsite_context_before,
                opts.callsite_context_after,
                combined,
            )
        else:
            if step < 1:
                step = 1
                if send_config.verbose:
                    _log.warn(
                        f"Step must be at least 1. Setting step to 1 for {self._platform}Notifier."
                    )

            return IterableWatch(
                iterable,
                step,
                total,
                _SendFnPartial(self._send, send_config),
                opts.label,
                opts.callsite_level or self._default_callsite_level,
                opts.callsite_context_before,
                opts.callsite_context_after,
                class_name,
                object_id,
            )

    def register(
        self,
        target: ModuleType | type[Any] | Any,
        name: str,
        params: str | list[str] | None = None,
        **options: Unpack[SendOptions],
    ) -> None:
        """
        Register existing function or method to be monitored by this notifier.
        This function corresponds to applying the :meth:`watch` decorator to an existing function or method.

        Args:
            target: The module, class, or class instance containing the function to be registered.
            name: The name of the function to be registered.
            params:
                Names of the function parameters whose values should be included in the message
                when the registered function is called.
            **options: Additional options. See :class:`SendOptions` for details.
        """
        self._register_impl(target, name, params, **options)

    def _register_impl(
        self,
        target: ModuleType | type[Any] | Any,
        name: str,
        params: str | list[str] | None = None,
        combined: int = 0,
        **options: Unpack[SendOptions],
    ) -> None:
        opts = _SendOptions(**options)
        original = getattr(target, name, None)
        if original is None:
            if opts.verbose if opts.verbose is not None else self._verbose:
                _log.error(
                    f"Cannot register {self._platform}Notifier on `{target.__name__}.{name}`: "
                    f"target `{target.__name__}` has no attribute `{name}`."
                )
            return
        watch: Watch | IterableWatch = self._watch_impl(
            params=params,
            combined=combined,
            **options,
        )
        assert isinstance(watch, Watch)
        patched = watch(original)
        setattr(target, name, patched)
        target_name = (
            target.__name__
            if hasattr(target, "__name__")
            else f"<{target.__class__.__name__} object at {hex(id(target))}>"
        )
        if opts.verbose if opts.verbose is not None else self._verbose:
            _log.info(f"Registered {self._platform}Notifier on `{target_name}.{name}`.")
