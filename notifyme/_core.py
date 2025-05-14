from __future__ import annotations

import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, ContextDecorator
from functools import wraps
from types import TracebackType
from typing import Any, Iterable, Literal, Type, cast, overload

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec
if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import notifyme._log as _log
from notifyme._base import ContextManagerDecorator, _BaseNotifier, _LevelStr
from notifyme._discord import DiscordNotifier
from notifyme._slack import SlackNotifier

_notifier = {}

_DESTINATIONS = Literal["slack", "discord"]
_DESTINATIONS_MAP: dict[_DESTINATIONS, Type[_BaseNotifier]] = {
    "slack": SlackNotifier,
    "discord": DiscordNotifier,
}


# NOTE: Python 3.12+ (PEP 695) supports inline type parameter syntax.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/reference/compound_stmts.html#type-params
P = ParamSpec("P")
R = ContextManagerDecorator | None


@overload
def allow_multi_dest(
    fn: Callable[P, ContextManagerDecorator],
) -> Callable[P, ContextManagerDecorator]: ...
@overload
def allow_multi_dest(fn: Callable[P, None]) -> Callable[P, None]: ...


def allow_multi_dest(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        send_to = kwargs.get("send_to")
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


@allow_multi_dest
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

    Args:
        send_to (str): The destination to send notifications to. Can be "slack" or "discord".
        verbose (bool): Whether to enable verbose logging.
        mention_to (str | None): The user to mention in the notification.
        mention_level (str): The level at which to mention the user.
        channel (str | None): The channel to send notifications to.
        token (str | None): The token for authentication.
        disable (bool): Whether to disable the notifier.
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


@allow_multi_dest
def send(
    data: Any,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    channel: str | None = None,
    mention_to: str | None = None,
    mention_level: _LevelStr | None = None,
    mention_if_ends: bool | None = None,
    verbose: bool | None = None,
    disable: bool | None = None,
) -> None:
    """
    Send a notification to the specified destination.

    Args:
        data (Any): The data to send in the notification.
        send_to (str): The destination to send notifications to. Can be "slack" or "discord".
        channel (str | None): The channel to send notifications to.
    """
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
    _notifier[send_to].send(data, **kwargs)  # type: ignore


@allow_multi_dest
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
    Decorator to watch a function and send notifications on errors.

    Args:
        send_to (str): The destination to send notifications to. Can be "slack" or "discord".
        channel (str | None): The channel to send notifications to.
        mention_to (str | None): The user to mention in the notification.
        mention_level (str): The level at which to mention the user.
        disable (bool): Whether to disable the notifier.
    """
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
