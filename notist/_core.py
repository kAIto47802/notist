from __future__ import annotations

import contextlib
import inspect
import itertools
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager, ContextDecorator
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Iterable,
    Literal,
    TypeVar,
    overload,
)

from notist import _log
from notist._notifiers.base import (
    BaseNotifier,
    ContextManagerDecorator,
    ContextManagerIterator,
    SendOptions,
)
from notist._notifiers.discord import DiscordNotifier
from notist._notifiers.slack import SlackNotifier

if sys.version_info >= (3, 10):
    from typing import ParamSpec
else:
    from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator
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

    if sys.version_info >= (3, 12):
        from typing import Unpack
    else:
        from typing_extensions import Unpack


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

# # NOTE: Python 3.10+ (PEP 604) supports writing union types with `X | Y`.
# # After dropping Python 3.9 support, we can remove using `typing.Union`.
# # See:
# #   - https://peps.python.org/pep-0604/
# #   - https://docs.python.org/3/library/stdtypes.html#types-union
if sys.version_info >= (3, 10):
    _R = ContextManagerDecorator | ContextManagerIterator | None
else:
    from typing import Union

    _R = Union[ContextManagerDecorator, None]


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
        if isinstance(send_to, Sequence) and not isinstance(send_to, str):
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
                if "combined" in inspect.signature(fn).parameters.keys():
                    new_kwargs["combined"] = len(send_to) - i
                res.append(fn(*args, **new_kwargs))  # type: ignore
            if _are_all_contexts(res):
                return _combine_contexts(res)
            elif all(r is None for r in res):
                return None
            else:
                raise ValueError("Cannot mix.")
        else:
            return fn(*args, **kwargs)

    return wrapper


def _combine_contexts(
    contexts: Sequence[AbstractContextManager],
) -> ContextManagerDecorator | ContextManagerIterator:
    class _CombinedBase(AbstractContextManager):
        def __enter__(self) -> Self:
            for ctx in contexts:
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


def _are_all_contexts(
    contexts: Sequence[object],
) -> TypeGuard[Sequence[AbstractContextManager]]:
    return all(isinstance(ctx, AbstractContextManager) for ctx in contexts)


class _PhantomContextManagerDecorator(ContextDecorator, contextlib.nullcontext):
    """A no-op context manager decorator that does nothing."""


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
    :func:`~notist._core.send`, and :func:`~notist._core.watch`.
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
    init_opts = SendOptions(
        channel=channel,
        mention_to=mention_to,
        verbose=verbose,
        disable=disable,
    )
    _init_if_needed(send_to, init_opts)
    print(init_opts)
    _notifiers[send_to].send(data, **init_opts)  # type: ignore


@overload
def watch(
    iterable: None = ...,
    /,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = ...,
    step: int = ...,
    total: None = ...,
    params: str | list[str] | None = ...,
    **options: Unpack[SendOptions],
) -> ContextManagerDecorator: ...


@overload
def watch(
    iterable: Iterable[T],
    /,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = ...,
    step: int = ...,
    total: int | None = ...,
    params: None = ...,
    **options: Unpack[SendOptions],
) -> ContextManagerIterator[T]: ...


def watch(
    iterable: Iterable[T] | None = None,
    /,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    params: str | list[str] | None = None,
    step: int = 1,
    total: int | None = None,
    **options: Unpack[SendOptions],
) -> ContextManagerDecorator | ContextManagerIterator[T]:
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
        **options: Additional options. See :class:`~notist._notifiers.base.SendOptions` for details.

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

        Use to monitor an iterable in a for loop:

        .. code-block:: python

           # Monitor progress of processing a long-running for loop
           for batch in notist.watch(train_dataloader, step=10):
               # This loop will be monitored, and you'll receive notifications every 10 iterations.
               # If an error occurs inside this loop, you'll be notified immediately.
               ...

    .. note::
       The above example does **not** catch exceptions automatically,
       since exceptions raised inside the for loop cannot be caught by the iterator in Python.
       If you also want to be notified when an error occurs, wrap your code in the monitoring context:

       .. code-block:: python

           with notist.watch(train_dataloader, step=10) as it:
               for batch in it:
                   # This loop will be monitored, and you'll receive notifications every 10 iterations.
                   # If an error occurs inside this context, you'll be notified immediately.
                   ...
    """
    return _watch_impl(
        iterable,
        send_to=send_to,
        params=params,
        step=step,
        total=total,
        **options,
    )


@_allow_multi_dest
def _watch_impl(
    iterable: Iterable[T] | None = None,
    /,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    params: str | list[str] | None = None,
    step: int = 1,
    total: int | None = None,
    combined: int = 0,
    class_name: str | None = None,
    object_id: int | None = None,
    **options: Unpack[SendOptions],
) -> ContextManagerDecorator | ContextManagerIterator[T]:
    if send_to is None:
        _warn_not_set_send_to()
        return (
            _PhantomContextManagerDecorator()
            if iterable is None
            else _PhantomContextManagerIterator(iterable)
        )
    assert isinstance(send_to, str)
    _init_if_needed(send_to, options)
    return _notifiers[send_to]._watch_impl(
        iterable,
        params=params,
        step=step,
        total=total,
        combined=combined,
        class_name=class_name,
        object_id=object_id,
        **options,
    )


def register(
    target: ModuleType | type[Any] | Any,
    name: str,
    params: str | list[str] | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    **options: Unpack[SendOptions],
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
        send_to:
            Destination(s) to send notifications to. e.g., "slack", "discord", or ["slack", "discord"].
        **options: Additional options. See :class:`~notist._notifiers.base.SendOptions` for details.

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
    _register_impl(
        target,
        name,
        params,
        send_to=send_to,
        **options,
    )


@_allow_multi_dest
def _register_impl(
    target: ModuleType | type[Any] | Any,
    name: str,
    params: str | list[str] | None = None,
    *,
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None,
    combined: int = 0,
    **options: Unpack[SendOptions],
) -> None:
    if send_to is None:
        _warn_not_set_send_to()
        return None
    assert isinstance(send_to, str)
    _init_if_needed(send_to, options)
    _notifiers[send_to]._register_impl(
        target,
        name,
        params,
        combined=combined,
        **options,
    )


def _init_if_needed(
    send_to: _DESTINATIONS | list[_DESTINATIONS],
    opts: SendOptions,
) -> None:
    if send_to not in _notifiers:
        init(
            send_to=send_to,
            **{  # type: ignore
                k: v
                for k, v in opts.items()
                if v is not None and v in inspect.signature(init).parameters.keys()
            },
        )
    _update_verbose(opts)


def _update_verbose(opts: SendOptions) -> None:
    opts["verbose"] = (verbose := opts.get("verbose")) and (
        verbose if isinstance(verbose, bool) else verbose >= 2
    )


def _warn_not_set_send_to() -> None:
    _log.warn(
        "No destination specified. "
        "Please specify `send_to` parameter or initialize notifier with `notist.init()`. "
        "No notifications will be sent."
    )
