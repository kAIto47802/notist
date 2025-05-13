from collections.abc import Callable
from functools import wraps
from typing import Any, Iterable, Literal, ParamSpec, Type, TypeVar

import notifyme._log as _log
from notifyme._base import _BaseNotifier, _LevelStr, _Watch
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
R = TypeVar("R")


def allow_multi_dist(fn: Callable[P, R]) -> Callable[P, R]:
    @wraps(fn)
    def wrapper(
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> R:
        if isinstance(kwargs["send_to"], Iterable) and not isinstance(send_to, str):
            for dest in kwargs["send_to"]:
                new_kwargs = kwargs.copy()
                new_kwargs["send_to"] = dest
                return fn(*args, **new_kwargs)  # type: ignore
            else:
                raise ValueError("the length of `send_to` must be greater than 0")
        else:
            return fn(*args, **kwargs)

    return wrapper


@allow_multi_dist
def init(
    send_to: _DESTINATIONS | list[_DESTINATIONS] = "slack",
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


@allow_multi_dist
def send(
    data: Any,
    send_to: _DESTINATIONS | list[_DESTINATIONS] = "slack",
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


@allow_multi_dist
def watch(
    label: str | None = None,
    send_to: _DESTINATIONS | list[_DESTINATIONS] = "slack",
    channel: str | None = None,
    mention_to: str | None = None,
    mention_level: _LevelStr = "error",
    mention_if_ends: bool = True,
    verbose: bool = True,
    disable: bool = False,
) -> _Watch:
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
    init(send_to, **{k: v for k, v in kwargs.items() if v is not None})  # type: ignore
