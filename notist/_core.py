from __future__ import annotations

import contextlib
import itertools
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager, ContextDecorator
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Literal,
    Protocol,
    TypeVar,
    overload,
    runtime_checkable,
)

from notist import _log
from notist._notifiers.base import (
    BaseNotifier,
    ContextManagerDecorator,
    ContextManagerIterator,
)
from notist._notifiers.discord import DiscordNotifier
from notist._notifiers.slack import SlackNotifier

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Sequence
    from types import ModuleType, TracebackType

    from notist._log import LevelStr

    if sys.version_info >= (3, 10):
        from typing import TypeGuard
    else:
        from typing_extensions import TypeGuard

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
_T = TypeVar("_T")
_P = ParamSpec("_P")
_F = TypeVar("_F", bound=Callable[..., Any])

# NOTE: Python 3.10+ (PEP 604) supports writing union types with `X | Y`.
# After dropping Python 3.9 support, we can remove using `typing.Union`.
# See:
#   - https://peps.python.org/pep-0604/
#   - https://docs.python.org/3/library/stdtypes.html#types-union
if sys.version_info >= (3, 10):
    _R = ContextManagerDecorator | ContextManagerIterator | None
else:
    from typing import Union

    _R = Union[ContextManagerDecorator, None]


@overload
def _allow_multi_dest(
    fn: Callable[_P, ContextManagerDecorator],
) -> Callable[_P, ContextManagerDecorator]: ...
@overload
def _allow_multi_dest(
    fn: Callable[_P, ContextManagerIterator[_T]],
) -> Callable[_P, ContextManagerIterator[_T]]: ...
@overload
def _allow_multi_dest(fn: Callable[_P, None]) -> Callable[_P, None]: ...


def _allow_multi_dest(fn: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(fn)
    def wrapper(
        *args: _P.args,
        **kwargs: _P.kwargs,
    ) -> _R:
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
                if i:
                    new_kwargs["verbose"] = 1
                res.append(fn(*args, **new_kwargs))  # type: ignore
            if _are_all_combinable(res):
                return _combine_contexts(res)
            elif all(r is None for r in res):
                return None
            else:
                raise ValueError("Cannot mix.")
        else:
            return fn(*args, **kwargs)

    return wrapper


@runtime_checkable
class _Combinable(Protocol):
    _combined: bool

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


def _combine_contexts(
    contexts: Sequence[_Combinable],
) -> ContextManagerDecorator | ContextManagerIterator:
    class _CombinedBase(AbstractContextManager):
        def __enter__(self) -> Self:
            for ctx in contexts:
                ctx._combined = True
                ctx.__enter__()
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc_val: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            for ctx in reversed(contexts):
                ctx.__exit__(exc_type, exc_val, tb)

    combined_cls: type[_CombinedBase]
    # cannot use TypeGuard here
    if all(callable(ctx) for ctx in contexts):

        class _CombinedContextManagerDecorator(_CombinedBase):
            def __call__(self, fn: _F) -> _F:
                wrapped = fn
                for ctx in contexts:
                    assert callable(ctx)
                    ctx._combined = True
                    wrapped = ctx(wrapped)
                return wrapped

        combined_cls = _CombinedContextManagerDecorator
    elif all(hasattr(ctx, "__iter__") for ctx in contexts):

        class _CombinedContextManagerIterator(_CombinedBase):
            def __iter__(self) -> Iterator:
                return map(lambda x: x[0], zip(*contexts))

        combined_cls = _CombinedContextManagerIterator
    else:
        raise ValueError("Cannot mix context decorators and context iterators.")

    return combined_cls()


def _are_all_combinable(
    contexts: Sequence[object],
) -> TypeGuard[Sequence[_Combinable]]:
    return all(isinstance(ctx, _Combinable) for ctx in contexts)


class _PhantomContextManagerDecorator(ContextDecorator, contextlib.nullcontext):
    """A no-op context manager decorator that does nothing."""

    def __call__(self, fn: Callable) -> Any:
        return fn


class _PhantomContextManagerIterator(Iterable[_T], contextlib.nullcontext):
    """A no-op context manager iterator that does nothing."""

    def __init__(self, iterable: Iterable[_T]) -> None:
        self._iterable = iterable

    def __iter__(self) -> Generator[_T, None, None]:
        yield from self._iterable


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
    verbose: bool | int = True,
    disable: bool = False,
) -> None:
    """
    Initialize the notifier with default settings.
    This settings can be overridden at each call of :func:`~notist._core.register`,
    :func:`~notist._core.send`, :func:`~notist._core.watch`, and :func:`~notist._core.watch_iterable`.
    Alternatively, you can skip initialization with this function and provide all settings directly through
    these functions.

    Args:
        send_to: Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
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

    .. note::
       The destination (``send_to``) must be set, either in this :func:`~notist._core.init` function
       or as an argument to subsequent calls.

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
            f"{_DESTINATIONS_MAP[send_to].__name__} already initialized. Skipping."
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
           notist.send("Job finished!")

           # You can also send any Python data (it will be stringified)
           notist.send(data)
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
    _update_verbose(kwargs)
    _notifiers[send_to].send(data, **kwargs)  # type: ignore


@_allow_multi_dest
def watch(
    params: str | list[str] | None = None,
    *,
    label: str | None = None,
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
    This will automatically send notifications when the function or code block starts, ends, or raises
    an exception.

    Args:
        params:
            Names of the function parameters whose values should be included in the message
            when the decorated function is called.
            This option is ignored when used as a context manager.
        label:
            Optional label for the watch context.
            This label will be included in both notification messages and log entries.
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

           @notist.watch()
           def long_task():
               # This function will be monitored
               # Your long-running code here
               ...

        Use as a context manager to monitor a block of code:

        .. code-block:: python

           with notist.watch():
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
    _update_verbose(kwargs)
    return _notifiers[send_to].watch(
        params,
        label=label,
        callsite_context_before=callsite_context_before,
        callsite_context_after=callsite_context_after,
        **kwargs,  # type: ignore
    )


@_allow_multi_dest
def register(
    target: ModuleType | type[Any] | Any,
    name: str,
    params: str | list[str] | None = None,
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
        params:
            Names of the function parameters whose values should be included in the message
            when the registered function is called.
            This option is ignored when used as a context manager.
        send_to:
            Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        label:
            Optional label for the watch context.
            This label will be included in both notification messages and log entries.
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
           notist.register(requests, "get")

           # Now any time you call `requests.get`, it will be monitored
           response = requests.get("https://example.com/largefile.zip")

        Monitor existing methods of classes:

        .. code-block:: python

           from transformers import Trainer

           # Register the `train` method of the `Trainer` class
           notist.register(Trainer, "train")

           # Now any time you call `trainer.train()`, it will be monitored
           trainer = Trainer(model=...)
           trainer.train()

        Monitor existing methods of specific class instances:

        .. code-block:: python

           from transformers import Trainer

           # Create a Trainer instance
           trainer = Trainer(model=...)

           # Register the `train` method of the `trainer` instance
           notist.register(trainer, "train")

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
    _update_verbose(kwargs)
    _notifiers[send_to].register(
        target,
        name,
        params,
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
) -> ContextManagerIterator[T]:
    if send_to is None:
        _warn_not_set_send_to()
        return _PhantomContextManagerIterator(iterable)
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
    _update_verbose(kwargs)
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
) -> ContextManagerIterator[T]:
    """
    A generator that yields items from an iterable while sending notifications about the progress.
    This is useful for monitoring long-running tasks that process items from an iterable.

    Args:
        iterable: The iterable to watch.
        step: The number of items to process before sending a progress notification.
        total:
            The total number of items in the iterable.
            If not provided, it will not be included in the progress messages.
        send_to:
            Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        label:
            Optional label for the watch context.
            This label will be included in both notification messages and log entries.
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
            for batch in notist.watch_iterable(train_dataloader, step=10):
                # This loop will be monitored, and you'll receive notifications every 10 iterations.
                # If an error occurs inside this loop, you'll be notified immediately.
                ...

    .. note::
       The above example does **not** catch exceptions automatically,
       since exceptions raised inside the for loop cannot be caught by the iterator in Python.
       If you also want to be notified when an error occurs, wrap your code in the monitoring context:

       .. code-block:: python

          with notist.watch_iterable(train_dataloader, step=10) as it:
              for batch in it:
                  # This loop will be monitored, and you'll receive notifications every 10 iterations.
                  # If an error occurs inside this context, you'll be notified immediately.
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


def _update_verbose(kwargs: dict[str, Any]) -> None:
    kwargs["verbose"] = (verbose := kwargs["verbose"]) and (
        verbose if isinstance(verbose, bool) else verbose >= 2
    )


def _warn_not_set_send_to() -> None:
    _log.warn(
        "No destination specified. "
        "Please specify `send_to` parameter or initialize notifier with `notist.init()`. "
        "No notifications will be sent."
    )
