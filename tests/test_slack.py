from typing import Any

import pytest
from pytest import CaptureFixture, MonkeyPatch
from slack_sdk import WebClient

from notifyme._slack import SlackNotifier


class DummyClient:
    def __init__(self) -> None:
        self.sent: list[Any] = []

    def chat_postMessage(self, **kwargs: Any) -> None:
        self.sent.append(kwargs)


@pytest.fixture
def dummy_client(monkeypatch: MonkeyPatch) -> DummyClient:
    client = DummyClient()
    monkeypatch.setattr(WebClient, "__init__", lambda self, token: None)
    monkeypatch.setattr(WebClient, "chat_postMessage", client.chat_postMessage)
    return client


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
def test_slack_send(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
    mention_to: str | None,
    default_disable: bool,
    disable: bool | None,
    expected_disable: bool,
) -> None:
    slack = SlackNotifier(
        channel=default_channel,
        token="tok",
        disable=default_disable,
    )
    slack._client = dummy_client  # type: ignore
    slack.send("msg", channel=channel, mention_to=mention_to, disable=disable)
    if expected_disable or expected_channel is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"<{mention_to}>\nmsg" if mention_to else "msg",
                "channel": expected_channel,
                "attachments": None,
            }
        ]
    captured = capsys.readouterr()
    if default_disable:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not expected_disable and expected_channel is None:
        assert "No Slack channel specified." in captured.out


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
@parametrize_disable
def test_slack_with_watch_success(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
    default_disable: bool,
    disable: bool | None,
    expected_disable: bool,
) -> None:
    slack = SlackNotifier(token="tok", channel=default_channel, disable=default_disable)
    slack._client = dummy_client  # type: ignore
    with slack.watch(label=label, channel=channel, disable=disable):
        pass
    details = f" [{label}]" if label else ""
    if expected_disable or expected_channel is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"Start watching{details}...",
                "channel": expected_channel,
                "attachments": None,
            },
            {
                "text": f"Stop watching{details}.\nExecution time: 0s.",
                "channel": expected_channel,
                "attachments": None,
            },
        ]
    captured = capsys.readouterr()
    if default_disable:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not expected_disable and expected_channel is None:
        assert "No Slack channel specified." in captured.out


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_slack_with_watch_error(
    dummy_client: DummyClient,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    slack = SlackNotifier(token="tok", channel=default_channel)
    slack._client = dummy_client  # type: ignore
    with pytest.raises(Exception):
        with slack.watch(label=label, channel=channel):
            raise Exception("This is an error")
    details = f" [{label}]" if label else ""
    if expected_channel is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent[0] == {
            "text": f"Start watching{details}...",
            "channel": expected_channel,
            "attachments": None,
        }
        assert (
            dummy_client.sent[1]["text"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert dummy_client.sent[1]["channel"] == expected_channel
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_slack_watch_decorator_success(
    dummy_client: DummyClient,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    slack = SlackNotifier(token="tok", channel=default_channel)
    slack._client = dummy_client  # type: ignore

    @slack.watch(label=label, channel=channel)
    def with_success() -> None:
        pass

    with_success()
    details = (
        f" [{label}, function: with_success]" if label else " [function: with_success]"
    )
    if expected_channel is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"Start watching{details}...",
                "channel": expected_channel,
                "attachments": None,
            },
            {
                "text": f"Stop watching{details}.\nExecution time: 0s.",
                "channel": expected_channel,
                "attachments": None,
            },
        ]


@pytest.mark.parametrize("label", ["label1", None])
@parametrize_channel
def test_slack_watch_decorator_error(
    dummy_client: DummyClient,
    label: str | None,
    default_channel: str | None,
    channel: str | None,
    expected_channel: str | None,
) -> None:
    slack = SlackNotifier(token="tok", channel=default_channel)
    slack._client = dummy_client  # type: ignore

    @slack.watch(label=label, channel=channel)
    def with_error() -> None:
        raise Exception("This is an error")

    with pytest.raises(Exception):
        with_error()

    details = (
        f" [{label}, function: with_error]" if label else " [function: with_error]"
    )
    if expected_channel is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent[0] == {
            "text": f"Start watching{details}...",
            "channel": expected_channel,
            "attachments": None,
        }
        assert (
            dummy_client.sent[1]["text"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert dummy_client.sent[1]["channel"] == expected_channel
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )
