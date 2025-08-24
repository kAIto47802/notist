from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

import pytest
from pytest import CaptureFixture, MonkeyPatch
from slack_sdk import WebClient

from notist._log import _CSI, _PREFIX, LEVEL_ORDER, LevelStr
from notist._notifiers.slack import SlackNotifier


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
        _OverrideTestCase(None, None, None),
        _OverrideTestCase("default-channel", None, "default-channel"),
        _OverrideTestCase(None, "test-channel", "test-channel"),
        _OverrideTestCase("default-channel", "test-channel", "test-channel"),
    ],
)

parametrize_mention_to = pytest.mark.parametrize(
    "mention_to",
    [
        _OverrideTestCase(None, None, None),
        _OverrideTestCase("@U0123456789", None, "@U0123456789"),
        _OverrideTestCase(None, "@U9876543210", "@U9876543210"),
        _OverrideTestCase("@U0123456789", "@U9876543210", "@U9876543210"),
    ],
)

parametrize_mention_level = pytest.mark.parametrize(
    "mention_level",
    [
        _OverrideTestCase("info", None, "info"),
        _OverrideTestCase("warning", None, "warning"),
        _OverrideTestCase("error", None, "error"),
        _OverrideTestCase("info", "warning", "warning"),
        _OverrideTestCase("info", "error", "error"),
        _OverrideTestCase("warning", "info", "info"),
        _OverrideTestCase("warning", "error", "error"),
        _OverrideTestCase("error", "info", "info"),
        _OverrideTestCase("error", "warning", "warning"),
    ],
)

parametrize_mention_if_ends = pytest.mark.parametrize(
    "mention_if_ends",
    [
        _OverrideTestCase(False, None, False),
        _OverrideTestCase(True, None, True),
        _OverrideTestCase(False, True, True),
        _OverrideTestCase(True, True, True),
        _OverrideTestCase(False, False, False),
        _OverrideTestCase(True, False, False),
    ],
)

parametrize_verbose = pytest.mark.parametrize(
    "verbose",
    [
        _OverrideTestCase(False, None, False),
        _OverrideTestCase(True, None, True),
        _OverrideTestCase(False, True, True),
        _OverrideTestCase(True, True, True),
        _OverrideTestCase(False, False, False),
        _OverrideTestCase(True, False, False),
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
        assert _PREFIX not in captured.out
        return
    else:
        assert _PREFIX in captured.out
    if disable.default and verbose.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None and verbose.expected:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_mention_to
@parametrize_mention_level
@parametrize_mention_if_ends
@parametrize_verbose
@parametrize_disable
def test_slack_watch_context_success(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    mention_to: _OverrideTestCase[str | None, str | None, str | None],
    mention_level: _OverrideTestCase[LevelStr, LevelStr | None, LevelStr],
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
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert len(dummy_client.sent) == 2
        assert all(s["channel"] == channel.expected for s in dummy_client.sent)
        assert all(s["attachments"] is None for s in dummy_client.sent)
        assert all(_CSI not in s["text"] for s in dummy_client.sent)
        assert (
            f"<{mention_to.expected}>\n"
            if mention_to.expected
            and LEVEL_ORDER[mention_level.expected] <= LEVEL_ORDER["info"]
            else ""
        ) + "Start watching" in dummy_client.sent[0]["text"]
        assert (
            f"<{mention_to.expected}>\n"
            if mention_to.expected
            and (
                LEVEL_ORDER[mention_level.expected] <= LEVEL_ORDER["info"]
                or mention_if_ends.expected
            )
            else ""
        ) + "End watching" in dummy_client.sent[1]["text"]
        assert "Execution time: 0s" in dummy_client.sent[1]["text"]
    captured = capsys.readouterr()
    if not verbose.expected and not verbose.default:
        assert _PREFIX not in captured.out
        return
    else:
        assert _PREFIX in captured.out
    if disable.default and verbose.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None and verbose.expected:
        assert "No Slack channel specified." in captured.out


@parametrize_label
@parametrize_channel
@parametrize_mention_to
@parametrize_mention_level
@parametrize_verbose
@parametrize_disable
def test_slack_watch_context_error(
    dummy_client: DummyClient,
    capsys: CaptureFixture[str],
    label: str | None,
    channel: _OverrideTestCase[str | None, str | None, str | None],
    mention_to: _OverrideTestCase[str | None, str | None, str | None],
    mention_level: _OverrideTestCase[LevelStr, LevelStr | None, LevelStr],
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
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
    else:
        assert len(dummy_client.sent) == 2
        assert all(s["channel"] == channel.expected for s in dummy_client.sent)
        assert all(_CSI not in s["text"] for s in dummy_client.sent)
        assert dummy_client.sent[0]["attachments"] is None
        assert "Start watching" in dummy_client.sent[0]["text"]
        assert (
            f"<{mention_to.expected}>\n"
            if mention_to.expected
            and LEVEL_ORDER[mention_level.expected] <= LEVEL_ORDER["error"]
            else ""
        ) + "Error while watching" in dummy_client.sent[1]["text"]
        assert dummy_client.sent[1]["channel"] == channel.expected
        assert (
            "Exception: This is an error"
            in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
        )
    captured = capsys.readouterr()
    if not verbose.expected and not verbose.default:
        assert _PREFIX not in captured.out
        return
    else:
        assert _PREFIX in captured.out
    if disable.default and verbose.default:
        assert "SlackNotifier is disabled. No messages will be sent." in captured.out
    if not disable.expected and channel.expected is None and verbose.expected:
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
    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    assert len(dummy_client.sent) == 2
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(s["attachments"] is None for s in dummy_client.sent)
    assert all(_CSI not in s["text"] for s in dummy_client.sent)
    assert "Start watching" in dummy_client.sent[0]["text"]
    assert "End watching" in dummy_client.sent[1]["text"]
    assert "Execution time: 0s" in dummy_client.sent[1]["text"]


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

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    assert len(dummy_client.sent) == 2
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(_CSI not in s["text"] for s in dummy_client.sent)
    assert "Start watching" in dummy_client.sent[0]["text"]
    assert "Error while watching" in dummy_client.sent[1]["text"]
    assert "This is an error" in dummy_client.sent[1]["text"]
    assert "Execution time: 0s" in dummy_client.sent[1]["text"]
    assert dummy_client.sent[1]["channel"] == channel.expected
    assert (
        "Exception: This is an error"
        in dummy_client.sent[1]["attachments"][0]["blocks"][0]["text"]["text"]
    )
    assert dummy_client.sent[-1]["attachments"] is not None


def test_slack_register_module(
    dummy_client: DummyClient,
) -> None:
    slack = SlackNotifier(token="tok", channel="test-channel")
    slack._client = dummy_client  # type: ignore

    import requests

    slack.register(requests, "get")
    requests.get("https://example.com")

    assert len(dummy_client.sent) == 2
    assert all(s["channel"] == "test-channel" for s in dummy_client.sent)
    assert all(s["attachments"] is None for s in dummy_client.sent)
    assert all(_CSI not in s["text"] for s in dummy_client.sent)
    assert "Start watching" in dummy_client.sent[0]["text"]
    assert "End watching" in dummy_client.sent[1]["text"]
    assert "Execution time: 0s" in dummy_client.sent[1]["text"]


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

    assert len(dummy_client.sent) == 6
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(s["attachments"] is None for s in dummy_client.sent)
    assert all("Start watching" in dummy_client.sent[i]["text"] for i in range(0, 6, 2))
    assert all("End watching" in dummy_client.sent[i]["text"] for i in range(1, 6, 2))
    assert all(_CSI not in s["text"] for s in dummy_client.sent)


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

    assert len(dummy_client.sent) == 4
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(s["attachments"] is None for s in dummy_client.sent)
    assert all("Start watching" in dummy_client.sent[i]["text"] for i in range(0, 4, 2))
    assert all("End watching" in dummy_client.sent[i]["text"] for i in range(1, 4, 2))
    assert all(_CSI not in s["text"] for s in dummy_client.sent)


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

    iterable = range(4)
    iterable_object = f"<range object at {hex(id(iterable))}>"
    for _ in slack.watch_iterable(
        iterable,
        step=step,
        total=total,
        label=label,
        channel=channel.override,
        disable=disable.override,
    ):
        pass

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    print(dummy_client.sent[-1]["text"])

    assert len(dummy_client.sent) == 2 * (4 // step + 1)
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(s["attachments"] is None for s in dummy_client.sent)
    assert all(_CSI not in s["text"] for s in dummy_client.sent)
    assert "Start watching" in dummy_client.sent[0]["text"]
    assert iterable_object in dummy_client.sent[0]["text"]
    assert "End watching" in dummy_client.sent[-1]["text"]
    assert iterable_object in dummy_client.sent[-1]["text"]
    assert "Total execution time" in dummy_client.sent[-1]["text"]

    if step == 1:
        if total is None:
            # Include white space so that it does not match "item 2–"
            assert "item 1 " in dummy_client.sent[1]["text"]
        else:
            assert f"item 1 of {total}" in dummy_client.sent[1]["text"]
    else:
        if total is None:
            assert "items 1–2" in dummy_client.sent[1]["text"]
        else:
            assert f"items 1–2 of {total}" in dummy_client.sent[1]["text"]


@parametrize_label
@parametrize_channel
@parametrize_disable
@pytest.mark.parametrize("step", [1, 2])
@pytest.mark.parametrize("total", [None, 3])
def test_slack_watch_iterable_error(
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

    with pytest.raises(Exception):
        for item in slack.watch_iterable(
            iterable,
            step=step,
            total=total,
            label=label,
            channel=channel.override,
            disable=disable.override,
        ):
            if item == 1:
                raise Exception("This is an error.")

    if disable.expected or channel.expected is None:
        assert dummy_client.sent == []
        return

    assert len(dummy_client.sent) == (5 if step == 1 else 3)
    assert all(s["channel"] == channel.expected for s in dummy_client.sent)
    assert all(_CSI not in s["text"] for s in dummy_client.sent)

    assert "Start watching" in dummy_client.sent[0]["text"]
    assert iterable_object in dummy_client.sent[0]["text"]
    assert dummy_client.sent[0]["attachments"] is None

    assert "Error while processing" in dummy_client.sent[-1]["text"]
    assert iterable_object in dummy_client.sent[-1]["text"]
    assert "Execution time" in dummy_client.sent[-1]["text"]
    assert "Total execution time: 0s" in dummy_client.sent[-1]["text"]
    assert dummy_client.sent[-1]["attachments"] is None

    if step == 1:
        if total is None:
            # Include white space so that it does not match "item 2–"
            assert "item 2 " in dummy_client.sent[-1]["text"]
        else:
            assert f"item 2 of {total}" in dummy_client.sent[-1]["text"]
    else:
        if total is None:
            assert "items 1–2" in dummy_client.sent[-1]["text"]
        else:
            assert "items 1–2" in dummy_client.sent[-1]["text"]
