from __future__ import annotations

import os
import warnings
from collections.abc import Callable
from functools import partial
from typing import Any

from slack_sdk import WebClient

from notifyme._base import _BaseNotifier, _LevelType, _Watch


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
        tb: str | None = None,
        level: _LevelType = "info",
        *,
        channel: str | None = None,
    ) -> None:
        channel = channel or self._default_channel
        if channel is None:
            raise ValueError("Either channel or default_channel must be set")
        self._client.chat_postMessage(
            text=str(data),
            channel=channel,
            attachments=tb
            and [
                {
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "plain_text",
                                "text": tb,
                            },
                        }
                    ],
                    "color": "#ff3d33",
                }
            ],
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
        self._send = partial(send_fn, channel=channel)
