from __future__ import annotations

from contextlib import ContextDecorator
from typing import TYPE_CHECKING

import notist._core

from .notifiers_test.test_discord import dummy_post  # noqa: F401
from .notifiers_test.test_slack import dummy_client  # noqa: F401

if TYPE_CHECKING:
    import sys
    from typing import Any

    from pytest import CaptureFixture, MonkeyPatch

    from notist._notifiers.base import BaseNotifier

    from .notifiers_test.test_discord import Sent
    from .notifiers_test.test_slack import DummyClient

    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self

import pytest

from notist._core import (
    _DESTINATIONS,
    _allow_multi_dest,
    _combine_contexts,
)


@_allow_multi_dest
def dummy_send(
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None, **kwargs: Any
) -> None:
    return None


@pytest.mark.parametrize(
    "send_to",
    [
        None,
        "slack",
        ["slack", "discord"],
    ],
)
def test_allow_multi_dest(send_to: _DESTINATIONS | list[_DESTINATIONS]) -> None:
    assert dummy_send(send_to=send_to) is None


def test_wo_specify_dest() -> None:
    assert dummy_send() is None


def test_combine_contexts_order() -> None:
    called = []

    class A(ContextDecorator):
        def __enter__(self) -> Self:
            called.append("A+")
            return self

        def __exit__(self, *e: Any) -> None:
            called.append("A-")

    class B(ContextDecorator):
        def __enter__(self) -> Self:
            called.append("B+")
            return self

        def __exit__(self, *e: Any) -> None:
            called.append("B-")

    combo = _combine_contexts([A(), B()])  # type: ignore
    with combo:
        called.append("BODY")
    assert called == ["A+", "B+", "BODY", "B-", "A-"]


parametrize_destination = pytest.mark.parametrize(
    "destination",
    ["slack", "discord", ["slack"], ["slack", "discord"]],
)


@parametrize_destination
def test_init(
    monkeypatch: MonkeyPatch,
    destination: _DESTINATIONS | list[_DESTINATIONS],
) -> None:
    dummy_notifiers: dict[str, BaseNotifier] = {}
    monkeypatch.setattr(notist._core, "_notifiers", dummy_notifiers)
    notist.init(send_to=destination, token="tok")
    if isinstance(destination, str):
        destination = [destination]
    assert set(dummy_notifiers.keys()) == set(destination)
    notist.init(send_to=destination, token="tok")
    assert set(dummy_notifiers.keys()) == set(destination)


@parametrize_destination
def test_send(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
    dummy_client: DummyClient,  # noqa
    dummy_post: Sent,  # noqa
    destination: _DESTINATIONS | list[_DESTINATIONS],
) -> None:
    dummy_notifiers: dict[str, BaseNotifier] = {}
    monkeypatch.setattr(notist._core, "_notifiers", dummy_notifiers)
    notist.init(send_to=destination, token="tok", channel="chan")
    if isinstance(destination, str):
        destination = [destination]
    if "slack" in dummy_notifiers:
        dummy_notifiers["slack"]._client = dummy_client  # type: ignore
    notist.send("msg")
    if "slack" in destination:
        assert len(dummy_client.sent) == 1
        assert dummy_client.sent[0]["text"] == "msg"
    else:
        assert dummy_client.sent == []
    if "discord" in destination:
        assert len(dummy_post) == 1
        assert dummy_post[0][2]["content"] == "msg"
    else:
        assert len(dummy_post) == 0

    captured = capsys.readouterr()
    if "slack" == destination or "slack" in destination:
        assert "SlackNotifier initialized" in captured.out
    if "discord" == destination or "discord" in destination:
        assert "DiscordNotifier initialized" in captured.out
    assert captured.out.count("msg") == 1
