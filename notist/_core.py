from __future__ import annotations

import itertools
import sys
from collections.abc import Generator
from contextlib import AbstractContextManager, ContextDecorator
from functools import wraps
from typing import TYPE_CHECKING, Iterable, Literal, TypeVar, cast, overload

import notist._log as _log
from notist._notifiers.base import BaseNotifier, ContextManagerDecorator
from notist._notifiers.discord import DiscordNotifier
from notist._notifiers.slack import SlackNotifier

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType, TracebackType
    from typing import Any

    from notist._log import LevelStr

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


_notifiers: dict[str, BaseNotifier] = {}

_DESTINATIONS = Literal["slack", "discord"]
_DESTINATIONS_MAP: dict[_DESTINATIONS, type[BaseNotifier]] = {
    "slack": SlackNotifier,
    "discord": DiscordNotifier,
}


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
T = TypeVar("T")
P = ParamSpec("P")

# NOTE: Python 3.10+ (PEP 604) supports writing union types with `X | Y`.
# After dropping Python 3.9 support, we can remove using `typing.Union`.
# See:
#   - https://peps.python.org/pep-0604/
#   - https://docs.python.org/3/library/stdtypes.html#types-union
if sys.version_info >= (3, 10):
    R = ContextManagerDecorator | Iterable | None
else:
    from typing import Union

    R = Union[ContextManagerDecorator, None]


@overload
def _allow_multi_dest(
    fn: Callable[P, ContextManagerDecorator],
) -> Callable[P, ContextManagerDecorator]: ...
@overload
def _allow_multi_dest(fn: Callable[P, Iterable[T]]) -> Callable[P, Iterable[T]]: ...
@overload
def _allow_multi_dest(fn: Callable[P, None]) -> Callable[P, None]: ...


def _allow_multi_dest(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        send_to = kwargs.get("send_to")
        if send_to is None and _notifiers:
            send_to = list(_notifiers.keys())
        iterable = kwargs.get("iterable")
        if isinstance(send_to, Iterable) and not isinstance(send_to, str):
            res = []
            for i, dest in enumerate(send_to):
                new_kwargs = kwargs.copy()
                new_kwargs["send_to"] = dest
                if i and iterable is not None:
                    new_kwargs["iterable"] = itertools.repeat(None)
                    new_kwargs["class_name"] = iterable.__class__.__name__
                    new_kwargs["object_id"] = hex(id(iterable))
                res.append(fn(*args, **new_kwargs))  # type: ignore
            if all(isinstance(r, AbstractContextManager) for r in res):
                return _combine_contexts_or_iterable(
                    cast(list[ContextManagerDecorator], res)
                )
            elif all(isinstance(r, Generator) for r in res):
                return map(lambda x: x[0], zip(*res))
            elif all(r is None for r in res):
                return None
            else:
                raise ValueError(
                    "Cannot mix context decorators and non-context decorators."
                )
        else:
            return fn(*args, **kwargs)

    return wrapper


def _combine_contexts_or_iterable(
    contexts: list[ContextManagerDecorator],
) -> ContextManagerDecorator:
    class _Combined(ContextDecorator, AbstractContextManager):
        def __enter__(self) -> Self:
            for ctx in contexts:
                ctx.__enter__()
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            for ctx in reversed(contexts):
                ctx.__exit__(exc_type, exc_value, traceback)

        def __iter__(self) -> Iterable:
            return map(lambda x: x[0], zip(*contexts))

    return _Combined()  # type: ignore


class _PhantomContextManagerDecorator(ContextDecorator, AbstractContextManager):
    """A no-op context manager decorator that does nothing."""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pass

    def __call__(self, fn: Callable) -> Any:
        return fn


@_allow_multi_dest
def init(
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS],
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
    This settings can be overridden at each call of :func:`~notist.register`,
    :func:`~notist.send`, and :func:`~notist.watch`.
    Alternatively, you can skip initialization with this function and provide all settings directly through these functions.

    Args:
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
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

    .. note::
       The destination (`send_to`) must be set, either in this :func:`~notist.init` function
       or as an argument to the :func:`~notist.register`, :func:`~notist.send`, and :func:`~notist.watch`.

    Example:

        .. code-block:: python

           import notist

           # Set up Slack notifiers with defaults
           notist.init(send_to="slack", channel="my-channel", mention_to="@U012345678")
    """
    global _notifiers
    assert isinstance(send_to, str)
    if send_to in _notifiers:
        _log.warn(
            f"{_DESTINATIONS_MAP[send_to].__class__.__name__} already initialized. Skipping."
        )
        return
    _notifiers[send_to] = _DESTINATIONS_MAP[send_to](
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        callsite_level=callsite_level,
        token=token,
        verbose=verbose,
        disable=disable,
    )


@_allow_multi_dest
def send(
    data: Any,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        channel: Override the default channel for notifications.
        mention_to: Override the default entity to mention on notification.
        verbose: Override the default verbosity setting.
        disable: Override the default disable flag.

    Example:

        .. code-block:: python

           # Immediately send "Job finished!" to your Slack channel
           notist.send("Job finished!", send_to="slack")

           # You can also send any Python data (it will be stringified)
           notist.send(data, send_to="slack")
    """
    if send_to is None:
        _warn_not_set_send_to()
        return
    assert isinstance(send_to, str)
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    _notifiers[send_to].send(data, **kwargs)  # type: ignore


@_allow_multi_dest
def watch(
    label: str | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
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

    Example:

        Use as a decorator to monitor a function:

        .. code-block:: python

           @notist.watch(send_to="slack")
           def long_task():
               # This function will be monitored
               # Your long-running code here
               ...

        Use as a context manager to monitor a block of code:

        .. code-block:: python

           with notist.watch(send_to="slack"):
               # Code inside this block will be monitored
               # Your long-running code here
               ...
    """
    if send_to is None:
        _warn_not_set_send_to()
        return _PhantomContextManagerDecorator()
    assert isinstance(send_to, str)
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        callsite_level=callsite_level,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    return _notifiers[send_to].watch(
        label,
        callsite_context_before=callsite_context_before,
        callsite_context_after=callsite_context_after,
        **kwargs,  # type: ignore
    )


@_allow_multi_dest
def register(
    target: ModuleType | type[Any] | Any,
    name: str,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
    Register existing function or method to be watched by this notifier.
    This function corresponds to applying the :meth:`watch` decorator to an existing function or method.

    Args:
        target: The module, class, or class instance containing the function to be registered.
        name: The name of the function to be registered.
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
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

    Example:

        Monitor existing functions from libraries:

        .. code-block:: python

           import requests

           # Register the `get` function from the `requests` library
           notist.register(requests, "get", send_to="slack")

           # Now any time you call `requests.get`, it will be monitored
           response = requests.get("https://example.com/largefile.zip")

        Monitor existing methods of classes:

        .. code-block:: python

           from transformers import Trainer

           # Register the `train` method of the `Trainer` class
           notist.register(Trainer, "train", send_to="slack")

           # Now any time you call `trainer.train()`, it will be monitored
           trainer = Trainer(model=...)
           trainer.train()

        Monitor existing methods of specific class instances:

        .. code-block:: python

           from transformers import Trainer

           # Create a Trainer instance
           trainer = Trainer(model=...)

           # Register the `train` method of the `trainer` instance
           notist.register(trainer, "train", send_to="slack")

           # Now any time you call `trainer.train()`, it will be monitored
           trainer.train()
    """
    if send_to is None:
        _warn_not_set_send_to()
        return
    assert isinstance(send_to, str)
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        callsite_level=callsite_level,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    _notifiers[send_to].register(
        target,
        name,
        label=label,
        callsite_context_before=callsite_context_before,
        callsite_context_after=callsite_context_after,
        **kwargs,  # type: ignore
    )


@_allow_multi_dest
def _watch_iterable_impl(
    iterable: Iterable[T],
    step: int = 1,
    total: int | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
    class_name: str | None = None,
    object_id: int | None = None,
) -> Iterable[T]:
    if send_to is None:
        _warn_not_set_send_to()
        return iterable
    assert isinstance(send_to, str)
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        callsite_level=callsite_level,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    return _notifiers[send_to]._watch_iterable_impl(  # type: ignore
        iterable,
        step=step,
        total=total,
        label=label,
        callsite_context_before=callsite_context_before,
        callsite_context_after=callsite_context_after,
        class_name=class_name,
        object_id=object_id,
        **kwargs,  # type: ignore
    )


def watch_iterable(
    iterable: Iterable[T],
    step: int = 1,
    total: int | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        label: Optional label for the watch context. This label will be included in both notification messages and log entries.
        mention_to: Override the default entity to mention on notification.
        mention_level: Override the default mention threshold level.
        mention_if_ends: Override the default setting for whether to mention at the end of the watch.
        callsite_level: Override the default call-site source snippet threshold level.
        callsite_context_before: Number of lines of context to include before the call site.
        callsite_context_after: Number of lines of context to include after the call site.
        verbose: Override the default verbosity setting.
        disable: Override the default disable flag.


    Example:

        .. code-block:: python

            # Monitor progress of processing a long-running for loop
            for batch in notist.watch_iterable(train_dataloader, step=10, send_to="slack"):
                # This loop will be monitored, and you'll receive notifications every 10 iterations.
                # If an error occurs inside this loop, you'll be notified immediately.
                ...
    """
    return _watch_iterable_impl(
        iterable,
        step,
        total,
        send_to=send_to,
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
    )


def _init_if_needed(
    send_to: _DESTINATIONS | list[_DESTINATIONS] = "slack",
    channel: str | None = None,
    mention_to: str | None = None,
    mention_level: LevelStr | None = None,
    mention_if_ends: bool | None = None,
    callsite_level: LevelStr | None = None,
    verbose: bool | None = None,
    disable: bool | None = None,
) -> None:
    if send_to in _notifiers:
        return
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        callsite_level=callsite_level,
        verbose=verbose,
        disable=disable,
    )
    init(send_to=send_to, **{k: v for k, v in kwargs.items() if v is not None})  # type: ignore


def _warn_not_set_send_to() -> None:
    _log.warn(
        "No destination specified. "
        "Please specify `send_to` parameter or initialize notifier with `notist.init()`. "
        "No notifications will be sent."
    )
