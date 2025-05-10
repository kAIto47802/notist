from __future__ import annotations

import os
import warnings
from collections.abc import Callable
from typing import Any

from slack_sdk import WebClient

from notifyme._base import _BaseNotifier, _Watch


class SlackNotifier(_BaseNotifier):
    platform = "Slack"

    def __init__(
        self,
        verbose: bool = True,
        default_channel: str | None = None,
        slack_token: str | None = None,
    ) -> None:
        super().__init__(verbose=verbose)
        self._default_channel = default_channel
        self._client = WebClient(token=slack_token or os.getenv("SLACK_BOT_TOKEN"))
        if not default_channel:
            warnings.warn("No default channel set. Need to specify channel each time.")

    def _do_send(
        self,
        data: Any,
        *,
        channel: str | None = None,
    ) -> None:
        channel = channel or self._default_channel
        if channel is None:
            raise ValueError("Either channel or default_channel must be set")
        self._client.chat_postMessage(
            channel=channel,
            text=str(data),
        )

    def watch(
        self, label: str | None = None, *, channel: str | None = None
    ) -> _SlackWatch:
        return _SlackWatch(self._send, self._verbose, label, channel)


class _SlackWatch(_Watch):
    def __init__(
        self,
        send_fn: Callable[..., None],
        verbose: bool = True,
        label: str | None = None,
        channel: str | None = None,
    ) -> None:
        super().__init__(send_fn, verbose, label)
        self._channel = channel
        self._send = lambda d: send_fn(d, channel=self._channel)
