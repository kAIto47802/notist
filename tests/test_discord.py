from __future__ import annotations

from typing import Any

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


parametrize_channel = pytest.mark.parametrize(
    "default_channel, channel, expected_channel",
    [
        (None, None, None),
        ("default-channel", None, "default-channel"),
        (None, "test-channel", "test-channel"),
        ("default-channel", "test-channel", "test-channel"),
    ],
)
parametrize_disable = pytest.mark.parametrize(
    "default_disable, disable, expected_disable",
    [
        (False, None, False),
        (True, None, True),
        (False, True, True),
        (True, True, True),
        (False, False, False),
        (True, False, False),
    ],
)


@parametrize_channel
@pytest.mark.parametrize("mention_to", [None, "@U0123456789"])
@parametrize_disable
def test_discord_send(
    dummy_post: Sent,
    capsys: CaptureFixture[str],
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
    mention_to: str | None,
    default_disable: bool,
    disable: bool | None,
    expected_disable: bool,
) -> None:
    discord = DiscordNotifier(
        channel=default_channel,
        token="tok",
        disable=default_disable,
    )
    discord.send("msg", channel=channel, mention_to=mention_to, disable=disable)
    if expected_disable or expected_channel is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 1
        assert (
            dummy_post[0][0]
            == f"https://discord.com/api/v10/channels/{expected_channel}/messages"
        )
        assert dummy_post[0][1]["Authorization"] == "Bot tok"
        assert dummy_post[0][1]["Content-Type"] == "application/json"
        assert dummy_post[0][2]["content"] == (
            f"<{mention_to}>\nmsg" if mention_to else "msg"
        )
    captured = capsys.readouterr()
    if default_disable:
        assert "DiscordNotifier is disabled. No messages will be sent." in captured.out
    if not expected_disable and expected_channel is None:
        assert "No Discord channel ID specified." in captured.out


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
@parametrize_disable
def test_discord_with_watch_success(
    dummy_post: Sent,
    capsys: CaptureFixture[str],
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
    default_disable: bool,
    disable: bool | None,
    expected_disable: bool,
) -> None:
    discord = DiscordNotifier(
        token="tok", channel=default_channel, disable=default_disable
    )
    with discord.watch(label=label, channel=channel, disable=disable):
        pass
    details = f" [{label}]" if label else ""
    if expected_disable or expected_channel is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{expected_channel}/messages"
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
        assert dummy_post[0][2]["content"] == f"Start watching{details}..."
        assert (
            dummy_post[1][2]["content"]
            == f"Stop watching{details}.\nExecution time: 0s."
        )
    captured = capsys.readouterr()
    if default_disable:
        assert "DiscordNotifier is disabled. No messages will be sent." in captured.out
    if not expected_disable and expected_channel is None:
        assert "No Discord channel ID specified." in captured.out


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_discord_with_watch_error(
    dummy_post: Sent,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    discord = DiscordNotifier(token="tok", channel=default_channel)
    with pytest.raises(Exception):
        with discord.watch(label=label, channel=channel):
            raise Exception("This is an error")
    details = f" [{label}]" if label else ""
    if expected_channel is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{expected_channel}/messages"
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
        assert dummy_post[0][2]["content"] == f"Start watching{details}..."
        assert (
            dummy_post[1][2]["content"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert (
            "Exception: This is an error"
            in dummy_post[1][2]["embeds"][0]["description"]
        )


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_discord_watch_decorator_success(
    dummy_post: Sent,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    discord = DiscordNotifier(token="tok", channel=default_channel)

    @discord.watch(label=label, channel=channel)
    def with_success() -> None:
        pass

    with_success()
    details = (
        f" [{label}, function: with_success]" if label else " [function: with_success]"
    )
    if expected_channel is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{expected_channel}/messages"
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
        assert dummy_post[0][2]["content"] == f"Start watching{details}..."
        assert (
            dummy_post[1][2]["content"]
            == f"Stop watching{details}.\nExecution time: 0s."
        )


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_discord_watch_decorator_error(
    dummy_post: Sent,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    discord = DiscordNotifier(token="tok", channel=default_channel)

    @discord.watch(label=label, channel=channel)
    def with_error() -> None:
        raise Exception("This is an error")

    with pytest.raises(Exception):
        with_error()

    details = (
        f" [{label}, function: with_error]" if label else " [function: with_error]"
    )
    if expected_channel is None:
        assert dummy_post == []
    else:
        assert len(dummy_post) == 2
        assert (
            dummy_post[0][0]
            == dummy_post[1][0]
            == f"https://discord.com/api/v10/channels/{expected_channel}/messages"
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
        assert dummy_post[0][2]["content"] == f"Start watching{details}..."
        assert (
            dummy_post[1][2]["content"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert (
            "Exception: This is an error"
            in dummy_post[1][2]["embeds"][0]["description"]
        )
