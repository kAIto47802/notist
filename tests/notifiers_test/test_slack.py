from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar, cast

import pytest
from pytest import CaptureFixture, MonkeyPatch
from slack_sdk import WebClient

from notifystate._notifiers.slack import SlackNotifier


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
parametrize_label = pytest.mark.parametrize("label", ["label1", None])


@parametrize_channel
@pytest.mark.parametrize("mention_to", [None, "@U0123456789"])
@parametrize_disable
def test_slack_send(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    channel: _OverrideTestCase[str | None],
    mention_to: str | None,
    disable: _OverrideTestCase[bool | None],
) -> None:
    slack = SlackNotifier(
        channel=channel.default,
        token="tok",
        disable=cast(bool, disable.default),
    )
    slack._client = dummy_client  # type: ignore
    slack.send(
        "msg", channel=channel.override, mention_to=mention_to, disable=disable.override
    )
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"<{mention_to}>\nmsg" if mention_to else "msg",
                "channel": channel.expected,
                "attachments": None,
            }
        ]
    captured = capsys.readouterr()
    if disable.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_with_watch_success(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    slack = SlackNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    slack._client = dummy_client  # type: ignore
    with slack.watch(label=label, channel=channel.override, disable=disable.override):
        pass
    details = f" [{label}]" if label else ""
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"Start watching{details}...",
                "channel": channel.expected,
                "attachments": None,
            },
            {
                "text": f"End watching{details}.\nExecution time: 0s.",
                "channel": channel.expected,
                "attachments": None,
            },
        ]
    captured = capsys.readouterr()
    if disable.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_with_watch_error(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    slack = SlackNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    slack._client = dummy_client  # type: ignore
    with pytest.raises(Exception):
        with slack.watch(
            label=label, channel=channel.override, disable=disable.override
        ):
            raise Exception("This is an error")
    details = f" [{label}]" if label else ""
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent[0] == {
            "text": f"Start watching{details}...",
            "channel": channel.expected,
            "attachments": None,
        }
        assert (
            dummy_client.sent[1]["text"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert dummy_client.sent[1]["channel"] == channel.expected
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_watch_decorator_success(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    slack = SlackNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    slack._client = dummy_client  # type: ignore

    @slack.watch(label=label, channel=channel.override, disable=disable.override)
    def with_success() -> None:
        pass

    with_success()
    details = (
        f" [{label}|function: with_success]" if label else " [function: with_success]"
    )
    print(dummy_client.sent)
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"Start watching{details}...",
                "channel": channel.expected,
                "attachments": None,
            },
            {
                "text": f"End watching{details}.\nExecution time: 0s.",
                "channel": channel.expected,
                "attachments": None,
            },
        ]


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_watch_decorator_error(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None],
    disable: _OverrideTestCase[bool | None],
) -> None:
    slack = SlackNotifier(
        token="tok", channel=channel.default, disable=cast(bool, disable.default)
    )
    slack._client = dummy_client  # type: ignore

    @slack.watch(label=label, channel=channel.override, disable=disable.override)
    def with_error() -> None:
        raise Exception("This is an error")

    with pytest.raises(Exception):
        with_error()

    details = f" [{label}|function: with_error]" if label else " [function: with_error]"
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent[0] == {
            "text": f"Start watching{details}...",
            "channel": channel.expected,
            "attachments": None,
        }
        assert (
            dummy_client.sent[1]["text"]
            == f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert dummy_client.sent[1]["channel"] == channel.expected
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )
