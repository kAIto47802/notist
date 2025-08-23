from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

import pytest
import requests
from pytest import CaptureFixture, MonkeyPatch

from notifystate._notifiers.discord import DiscordNotifier

# NOTE: Python 3.12+ (PEP 695) supports type statement.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/library/typing.html#type-aliases
Sent = list[tuple[str, dict[str, str], dict[str, Any]]]


class DummyResponse:
    def __init__(self, ok: bool = True) -> None:
        self._ok = ok

    def raise_for_status(self) -> None:
        if not self._ok:
            raise requests.HTTPError("fail")


@pytest.fixture
def dummy_post(
    monkeypatch: MonkeyPatch,
) -> Sent:
    sent = []

    def fake_post(
        url: str, headers: dict[str, str], json: dict[str, Any]
    ) -> DummyResponse:
        sent.append((url, headers, json))
        return DummyResponse(ok=True)

    monkeypatch.setattr(requests, "post", fake_post)
    return sent


T = TypeVar("T")


# NOTE: Python 3.12+ (PEP 695) supports type-parameterized class .
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
@dataclass(frozen=True)
class _OverrideTestCase(Generic[T]):
    default: T
    override: T
    expected: T


# NOTE: It is sufficient for here to only test the `watch` and `send` methods,
# as the rest of the methods are inherited from `BaseNotifier` and tested in `SlackNotifier`.

parametrize_label = pytest.mark.parametrize("label", ["label1", None])

parametrize_channel = pytest.mark.parametrize(
    "channel",
    [
        _OverrideTestCase(None, None, None),
        _OverrideTestCase("default-channel", None, "default-channel"),
        _OverrideTestCase(None, "test-channel", "test-channel"),
        _OverrideTestCase("default-channel", "test-channel", "test-channel"),
    ],
)
parametrize_disable = pytest.mark.parametrize(
    "disable",
    [
        _OverrideTestCase(False, None, False),
        _OverrideTestCase(True, None, True),
        _OverrideTestCase(False, True, True),
        _OverrideTestCase(True, True, True),
        _OverrideTestCase(False, False, False),
        _OverrideTestCase(True, False, False),
    ],
)


@parametrize_channel
@pytest.mark.parametrize("mention_to", [None, "@U0123456789"])
@parametrize_disable
def test_discord_send(
    dummy_post: Sent,
    capsys: CaptureFixture[str],
    channel: _OverrideTestCase[str | None],
    mention_to: str | None,
    disable: _OverrideTestCase[bool | None],
) -> None:
    discord = DiscordNotifier(
        channel=channel.default,
        token="tok",
        disable=cast(bool, disable.default),
    )
    discord.send(
        "msg", channel=channel.override, mention_to=mention_to, disable=disable.override
    )
    if disable.expected or channel.expected is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 1
        assert (
            dummy_post[0][0]
            == f"https://discord.com/api/v10/channels/{channel.expected}/messages"
        )
        assert dummy_post[0][1]["Authorization"] == "Bot tok"
        assert dummy_post[0][1]["Content-Type"] == "application/json"
        assert dummy_post[0][2]["content"] == (
            f"<{mention_to}>\nmsg" if mention_to else "msg"
        )
    captured = capsys.readouterr()
    if disable.default:
        assert "DiscordNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Discord channel ID specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_discord_with_watch_success(
    dummy_post: Sent,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    discord = DiscordNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    with discord.watch(label=label, channel=channel.override, disable=disable.override):
        pass
    if disable.expected or channel.expected is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{channel.expected}/messages"
        )
        assert (
            dummy_post[0][1]["Authorization"]
            == dummy_post[1][1]["Authorization"]
            == "Bot tok"
        )
        assert (
            dummy_post[0][1]["Content-Type"]
            == dummy_post[1][1]["Content-Type"]
            == "application/json"
        )
        assert "Start watching" in dummy_post[0][2]["content"]
        assert "End watching" in dummy_post[1][2]["content"]
        assert "Execution time: 0s." in dummy_post[1][2]["content"]
    captured = capsys.readouterr()
    if disable.default:
        assert "DiscordNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Discord channel ID specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_discord_with_watch_error(
    dummy_post: Sent,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    discord = DiscordNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    with pytest.raises(Exception):
        with discord.watch(
            label=label, channel=channel.override, disable=disable.override
        ):
            raise Exception("This is an error")
    if disable.expected or channel.expected is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{channel.expected}/messages"
        )
        assert (
            dummy_post[0][1]["Authorization"]
            == dummy_post[1][1]["Authorization"]
            == "Bot tok"
        )
        assert (
            dummy_post[0][1]["Content-Type"]
            == dummy_post[1][1]["Content-Type"]
            == "application/json"
        )
        assert "Start watching" in dummy_post[0][2]["content"]
        assert "Error while watching" in dummy_post[1][2]["content"]
        assert "This is an error" in dummy_post[1][2]["content"]
        assert "Execution time: 0s." in dummy_post[1][2]["content"]
        assert (
            "Exception: This is an error"
            in dummy_post[1][2]["embeds"][0]["description"]
        )


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_discord_watch_decorator_success(
    dummy_post: Sent,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    discord = DiscordNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )

    @discord.watch(label=label, channel=channel.override, disable=disable.override)
    def with_success() -> None:
        pass

    with_success()
    if disable.expected or channel.expected is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{channel.expected}/messages"
        )
        assert (
            dummy_post[0][1]["Authorization"]
            == dummy_post[1][1]["Authorization"]
            == "Bot tok"
        )
        assert (
            dummy_post[0][1]["Content-Type"]
            == dummy_post[1][1]["Content-Type"]
            == "application/json"
        )
        assert "Start watching" in dummy_post[0][2]["content"]
        assert "End watching" in dummy_post[1][2]["content"]
        assert "Execution time: 0s." in dummy_post[1][2]["content"]


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_discord_watch_decorator_error(
    dummy_post: Sent,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    discord = DiscordNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )

    @discord.watch(label=label, channel=channel.override, disable=disable.override)
    def with_error() -> None:
        raise Exception("This is an error")

    with pytest.raises(Exception):
        with_error()

    if disable.expected or channel.expected is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{channel.expected}/messages"
        )
        assert (
            dummy_post[0][1]["Authorization"]
            == dummy_post[1][1]["Authorization"]
            == "Bot tok"
        )
        assert (
            dummy_post[0][1]["Content-Type"]
            == dummy_post[1][1]["Content-Type"]
            == "application/json"
        )
        assert "Start watching" in dummy_post[0][2]["content"]
        assert "Error while watching" in dummy_post[1][2]["content"]
        assert "This is an error" in dummy_post[1][2]["content"]
        assert "Execution time: 0s." in dummy_post[1][2]["content"]
        assert (
            "Exception: This is an error"
            in dummy_post[1][2]["embeds"][0]["description"]
        )
