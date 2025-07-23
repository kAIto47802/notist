from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, ContextDecorator
from functools import wraps
from types import ModuleType, TracebackType
from typing import Any, Iterable, Literal, Type, TypeVar, cast, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import notifystate._log as _log
from notifystate._notifiers.base import BaseNotifier, ContextManagerDecorator, _LevelStr
from notifystate._notifiers.discord import DiscordNotifier
from notifystate._notifiers.slack import SlackNotifier

_notifier: dict[str, BaseNotifier] = {}

_DESTINATIONS = Literal["slack", "discord"]
_DESTINATIONS_MAP: dict[_DESTINATIONS, Type[BaseNotifier]] = {
    "slack": SlackNotifier,
    "discord": DiscordNotifier,
}


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
# NOTE: PEP 604 (`X | Y`) union syntax requires Python 3.10+.
# For Python < 3.10 (e.g. 3.9), we need to use `typing.Union[X, Y]`.
# After dropping Python 3.9 support, we can remove using `typing.Union`.
P = ParamSpec("P")
if sys.version_info >= (3, 10):
    R = ContextManagerDecorator | None
else:
    from typing import Union

    R = Union[ContextManagerDecorator, None]


@overload
def _allow_multi_dest(
    fn: Callable[P, ContextManagerDecorator],
) -> Callable[P, ContextManagerDecorator]: ...
@overload
def _allow_multi_dest(fn: Callable[P, None]) -> Callable[P, None]: ...


def _allow_multi_dest(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        send_to = kwargs.get("send_to")
        if send_to is None and _notifier:
            send_to = list(_notifier.keys())
        if isinstance(send_to, Iterable) and not isinstance(send_to, str):
            res = []
            for dest in send_to:
                new_kwargs = kwargs.copy()
                new_kwargs["send_to"] = dest
                res.append(fn(*args, **new_kwargs))  # type: ignore
            if all(isinstance(r, AbstractContextManager) for r in res):
                return _combine_contexts(cast(list[ContextManagerDecorator], res))
            elif all(r is None for r in res):
                return None
            else:
                raise ValueError(
                    "Cannot mix context decorators and non-context decorators."
                )
        else:
            return fn(*args, **kwargs)

    return wrapper


def _combine_contexts(
    contexts: list[ContextManagerDecorator],
) -> ContextManagerDecorator:
    class _Combined(ContextDecorator, AbstractContextManager):
        def __enter__(self) -> Self:
            for ctx in contexts:
                ctx.__enter__()
            return self

        def __exit__(
            self,
            exc_type: Type[BaseException] | None,
            exc_value: BaseException | None,
            traceback: TracebackType | None,
        ) -> None:
            for ctx in reversed(contexts):
                ctx.__exit__(exc_type, exc_value, traceback)

    return _Combined()  # type: ignore


T = TypeVar("T")


class _PhantomContextManagerDecorator(ContextDecorator, AbstractContextManager):
    """A no-op context manager decorator that does nothing."""

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
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
    mention_level: _LevelStr = "error",
    mention_if_ends: bool = True,
    token: str | None = None,
    verbose: bool = True,
    disable: bool = False,
) -> None:
    """
    Initialize the notifier with the specified parameters.
    This settings can be overridden at each call of :func:`~notifystate.register`,
    :func:`~notifystate.send`, and :func:`~notifystate.watch`.


    Args:
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
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
    global _notifier
    assert isinstance(send_to, str)
    if send_to in _notifier:
        _log.warn(
            f"{_DESTINATIONS_MAP[send_to].__class__.__name__} already initialized. Skipping."
        )
        return
    _notifier[send_to] = _DESTINATIONS_MAP[send_to](
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
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
    _notifier[send_to].send(data, **kwargs)  # type: ignore


@_allow_multi_dest
def watch(
    label: str | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
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
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        channel: Override the default channel for notifications.
        mention_to: Override the default entity to mention on notification.
        mention_level: Override the default mention threshold level.
        mention_if_ends: Override the default setting for whether to mention at the end of the watch.
        verbose: Override the default verbosity setting.
        disable: Override the default disable flag.

    Returns:
        An an object that can serve as both a context manager and a decorator.
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
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    return _notifier[send_to].watch(label, **kwargs)  # type: ignore


@_allow_multi_dest
def register(
    target: ModuleType | Type[Any] | Any,
    name: str,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    label: str | None = None,
    channel: str | None = None,
    mention_to: str | None = None,
    mention_level: _LevelStr | None = None,
    mention_if_ends: bool | None = None,
    verbose: bool | None = None,
    disable: bool | None = None,
) -> None:
    """
    Register existing function or method to be watched by this notifier.
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
    if send_to is None:
        _warn_not_set_send_to()
        return
    assert isinstance(send_to, str)
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to=send_to, **kwargs)  # type: ignore
    _notifier[send_to].register(target, name, label=label, **kwargs)  # type: ignore


def _init_if_needed(
    send_to: _DESTINATIONS | list[_DESTINATIONS] = "slack",
    channel: str | None = None,
    mention_to: str | None = None,
    mention_level: _LevelStr | None = None,
    mention_if_ends: bool | None = None,
    verbose: bool | None = None,
    disable: bool | None = None,
) -> None:
    if send_to in _notifier:
        return
    kwargs = dict(
        channel=channel,
        mention_to=mention_to,
        mention_level=mention_level,
        mention_if_ends=mention_if_ends,
        verbose=verbose,
        disable=disable,
    )
    init(send_to=send_to, **{k: v for k, v in kwargs.items() if v is not None})  # type: ignore


def _warn_not_set_send_to() -> None:
    _log.warn(
        "No destination specified. "
        "Please specify `send_to` parameter or initialize notifier with `notifystate.init()`. "
        "No notifications will be sent."
    )
