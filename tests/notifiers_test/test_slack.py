from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

import pytest
from pytest import CaptureFixture, MonkeyPatch
from slack_sdk import WebClient

from notifystate._notifiers.base import _LEVEL_ORDER, _LevelStr
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
U = TypeVar("U")
V = TypeVar("V")


# NOTE: Python 3.12+ (PEP 695) supports type-parameterized class .
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
@dataclass(frozen=True)
class _OverrideTestCase(Generic[T, U, V]):
    default: T
    override: U
    expected: V


# NOTE: In order to check BaseNotifier's behavior, every method is tested.

parametrize_label = pytest.mark.parametrize("label", ["label1", None])

parametrize_channel = pytest.mark.parametrize(
    "channel",
    [
        # _OverrideTestCase(None, None, None),
        _OverrideTestCase("default-channel", None, "default-channel"),
        # _OverrideTestCase(None, "test-channel", "test-channel"),
        # _OverrideTestCase("default-channel", "test-channel", "test-channel"),
    ],
)

parametrize_mention_to = pytest.mark.parametrize(
    "mention_to",
    [
        # _OverrideTestCase(None, None, None),
        # _OverrideTestCase("@U0123456789", None, "@U0123456789"),
        # _OverrideTestCase(None, "@U9876543210", "@U9876543210"),
        _OverrideTestCase("@U0123456789", "@U9876543210", "@U9876543210"),
    ],
)

parametrize_mention_level = pytest.mark.parametrize(
    "mention_level",
    [
        # _OverrideTestCase("info", None, "info"),
        # _OverrideTestCase("warning", None, "warning"),
        # _OverrideTestCase("error", None, "error"),
        # _OverrideTestCase("info", "warning", "warning"),
        # _OverrideTestCase("info", "error", "error"),
        # _OverrideTestCase("warning", "info", "info"),
        # _OverrideTestCase("warning", "error", "error"),
        # _OverrideTestCase("error", "info", "info"),
        _OverrideTestCase("error", "warning", "warning"),
    ],
)

parametrize_mention_if_ends = pytest.mark.parametrize(
    "mention_if_ends",
    [
        _OverrideTestCase(False, None, False),
        # _OverrideTestCase(True, None, True),
        # _OverrideTestCase(False, True, True),
        # _OverrideTestCase(True, True, True),
        # _OverrideTestCase(False, False, False),
        # _OverrideTestCase(True, False, False),
    ],
)

parametrize_verbose = pytest.mark.parametrize(
    "verbose",
    [
        _OverrideTestCase(False, None, False),
        # _OverrideTestCase(True, None, True),
        # _OverrideTestCase(False, True, True),
        # _OverrideTestCase(True, True, True),
        # _OverrideTestCase(False, False, False),
        # _OverrideTestCase(True, False, False),
    ],
)

parametrize_disable = pytest.mark.parametrize(
    "disable",
    [
        _OverrideTestCase(False, None, False),
        # _OverrideTestCase(True, None, True),
        # _OverrideTestCase(False, True, True),
        # _OverrideTestCase(True, True, True),
        # _OverrideTestCase(False, False, False),
        # _OverrideTestCase(True, False, False),
    ],
)


@parametrize_channel
@parametrize_mention_to
@parametrize_verbose
@parametrize_disable
def test_slack_send(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    channel: _OverrideTestCase[str | None, str | None, str | None],
    mention_to: _OverrideTestCase[str | None, str | None, str | None],
    verbose: _OverrideTestCase[bool, bool | None, bool],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(
        channel=channel.default,
        token="tok",
        mention_to=mention_to.default,
        verbose=verbose.default,
        disable=disable.default,
    )
    slack._client = dummy_client  # type: ignore
    slack.send(
        "msg",
        channel=channel.override,
        mention_to=mention_to.override,
        verbose=verbose.override,
        disable=disable.override,
    )
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": f"<{mention_to.expected}>\nmsg"
                if mention_to.expected
                else "msg",
                "channel": channel.expected,
                "attachments": None,
            }
        ]
    captured = capsys.readouterr()
    if not verbose.expected and not verbose.default:
        assert "[NotifyState]" not in captured.out
        return
    else:
        assert "[NotifyState]" in captured.out
    if disable.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_mention_to
@parametrize_mention_level
@parametrize_mention_if_ends
@parametrize_verbose
@parametrize_disable
def test_slack_with_watch_success(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    mention_to: _OverrideTestCase[str | None, str | None, str | None],
    mention_level: _OverrideTestCase[_LevelStr, _LevelStr | None, _LevelStr],
    mention_if_ends: _OverrideTestCase[bool, bool | None, bool],
    verbose: _OverrideTestCase[bool, bool | None, bool],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(
        token="tok",
        channel=channel.default,
        mention_to=mention_to.default,
        mention_level=mention_level.default,
        mention_if_ends=mention_if_ends.default,
        verbose=verbose.default,
        disable=disable.default,
    )
    slack._client = dummy_client  # type: ignore
    with slack.watch(
        label=label,
        channel=channel.override,
        mention_to=mention_to.override,
        mention_level=mention_level.override,
        mention_if_ends=mention_if_ends.override,
        verbose=verbose.override,
        disable=disable.override,
    ):
        pass
    details = f" [{label}]" if label else ""
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert dummy_client.sent == [
            {
                "text": (
                    f"<{mention_to.expected}>\n"
                    if mention_to.expected
                    and _LEVEL_ORDER[mention_level.expected] <= _LEVEL_ORDER["info"]
                    else ""
                )
                + f"Start watching{details}...",
                "channel": channel.expected,
                "attachments": None,
            },
            {
                "text": (
                    f"<{mention_to.expected}>\n"
                    if mention_to.expected
                    and (
                        _LEVEL_ORDER[mention_level.expected] <= _LEVEL_ORDER["info"]
                        or mention_if_ends.expected
                    )
                    else ""
                )
                + f"End watching{details}.\nExecution time: 0s.",
                "channel": channel.expected,
                "attachments": None,
            },
        ]
    captured = capsys.readouterr()
    if not verbose.expected and not verbose.default:
        assert "[NotifyState]" not in captured.out
        return
    else:
        assert "[NotifyState]" in captured.out
    if disable.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_mention_to
@parametrize_mention_level
@parametrize_verbose
@parametrize_disable
def test_slack_with_watch_error(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    mention_to: _OverrideTestCase[str | None, str | None, str | None],
    mention_level: _OverrideTestCase[_LevelStr, _LevelStr | None, _LevelStr],
    verbose: _OverrideTestCase[bool, bool | None, bool],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(
        token="tok",
        channel=channel.default,
        mention_to=mention_to.default,
        mention_level=mention_level.default,
        verbose=verbose.default,
        disable=disable.default,
    )
    slack._client = dummy_client  # type: ignore
    with pytest.raises(Exception):
        with slack.watch(
            label=label,
            channel=channel.override,
            mention_to=mention_to.override,
            mention_level=mention_level.override,
            verbose=verbose.override,
            disable=disable.override,
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
            == (
                f"<{mention_to.expected}>\n"
                if mention_to.expected
                and _LEVEL_ORDER[mention_level.expected] <= _LEVEL_ORDER["error"]
                else ""
            )
            + f"Error while watching{details}: This is an error\nExecution time: 0s."
        )
        assert dummy_client.sent[1]["channel"] == channel.expected
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )
    captured = capsys.readouterr()
    if not verbose.expected and not verbose.default:
        assert "[NotifyState]" not in captured.out
        return
    else:
        assert "[NotifyState]" in captured.out
    if disable.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_watch_decorator_success(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(token="tok", channel=channel.default, disable=disable.default)
    slack._client = dummy_client  # type: ignore

    @slack.watch(label=label, channel=channel.override, disable=disable.override)
    def with_success() -> None:
        pass

    with_success()
    details = (
        f" [{label}|function: with_success]" if label else " [function: with_success]"
    )
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
    channel: _OverrideTestCase[str | None, str | None, str | None],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(token="tok", channel=channel.default, disable=disable.default)
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


def test_slack_register_module(
    dummy_client: DummyClient,
) -> None:
    slack = SlackNotifier(token="tok", channel="test-channel")
    slack._client = dummy_client  # type: ignore

    import requests

    slack.register(requests, "get")
    requests.get("https://example.com")

    assert dummy_client.sent == [
        {
            "text": "Start watching [function: get]...",
            "channel": "test-channel",
            "attachments": None,
        },
        {
            "text": "End watching [function: get].\nExecution time: 0s.",
            "channel": "test-channel",
            "attachments": None,
        },
    ]


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_register_class(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(token="tok", channel=channel.default, disable=disable.default)
    slack._client = dummy_client  # type: ignore

    class DummyClass:
        def method(self) -> None:
            pass

    slack.register(
        DummyClass,
        "method",
        label=label,
        channel=channel.override,
        disable=disable.override,
    )
    instance1 = DummyClass()
    instance1.method()
    instance1.method()
    instance2 = DummyClass()
    instance2.method()

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    details = f" [{label}|function: method]" if label else " [function: method]"
    assert (
        dummy_client.sent
        == [
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
        * 3
    )


@parametrize_label
@parametrize_channel
@parametrize_disable
def test_slack_register_instance(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    disable: _OverrideTestCase[bool, bool | None, bool],
) -> None:
    slack = SlackNotifier(token="tok", channel=channel.default, disable=disable.default)
    slack._client = dummy_client  # type: ignore

    class DummyClass:
        def method(self) -> None:
            pass

    instance1 = DummyClass()

    slack.register(
        instance1,
        "method",
        label=label,
        channel=channel.override,
        disable=disable.override,
    )
    instance1.method()
    instance1.method()
    instance2 = DummyClass()
    instance2.method()

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    details = f" [{label}|function: method]" if label else " [function: method]"
    assert (
        dummy_client.sent
        == [
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
        * 2
    )


@parametrize_label
@parametrize_channel
@parametrize_disable
@pytest.mark.parametrize("step", [1, 2])
@pytest.mark.parametrize("total", [None, 3])
def test_slack_watch_iterable_success(
    dummy_client: DummyClient,
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    disable: _OverrideTestCase[bool, bool | None, bool],
    step: int,
    total: int | None,
) -> None:
    slack = SlackNotifier(token="tok", channel=channel.default, disable=disable.default)
    slack._client = dummy_client  # type: ignore

    iterable = range(3)
    iterable_object = f"<range object at {hex(id(iterable))}>"
    for _ in slack.watch_iterable(
        iterable,
        label=label,
        channel=channel.override,
        disable=disable.override,
    ):
        pass

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    details = f" {iterable_object} [{label}]" if label else f" {iterable_object}"

    if step == 1:
        if total is None:
            assert dummy_client.sent == [
                {
                    "text": f"Start watching{details}...",
                    "channel": channel.expected,
                    "attachments": None,
                },
                *sum(
                    [
                        [
                            {
                                "text": f"Processing item {i} from {iterable_object}...",
                                "channel": channel.expected,
                                "attachments": None,
                            },
                            {
                                "text": (
                                    f"Processed item {i} from {iterable_object}.\n"
                                    f"Execution time for item {i}: 0s.\n"
                                    f"Total execution time: 0s."
                                ),
                                "channel": channel.expected,
                                "attachments": None,
                            },
                        ]
                        for i in range(1, 4)
                    ],
                    [],
                ),
                {
                    "text": f"End watching{details}.\nTotal execution time: 0s.",
                    "channel": channel.expected,
                    "attachments": None,
                },
            ]
