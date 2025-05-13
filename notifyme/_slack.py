from __future__ import annotations

import os
from functools import partial
from typing import Any

from slack_sdk import WebClient

import notifyme._log as _log
from notifyme._base import _LEVEL_ORDER, _BaseNotifier, _LevelStr, _Watch


class SlackNotifier(_BaseNotifier):
    platform = "Slack"

    def __init__(
        self,
        verbose: bool = True,
        mention_to: str | None = None,
        mention_level: _LevelStr = "error",
        channel: str | None = None,
        slack_token: str | None = None,
        disable: bool = False,
    ) -> None:
        super().__init__(verbose, mention_to, mention_level, disable)
        self._default_channel = channel
        self._client = WebClient(token=slack_token or os.getenv("SLACK_BOT_TOKEN"))
        if not self._disable:
            if channel:
                _log.info(f"SlackNotifier initialized with default channel: {channel}")
            else:
                _log.warn(
                    "No Slack channel configured. Need to specify channel each time."
                )

    def _do_send(
        self,
        data: Any,
        tb: str | None = None,
        level: _LevelStr = "info",
        *,
        channel: str | None = None,
    ) -> None:
        channel = channel or self._default_channel
        if channel is None:
            _log.error(
                "No Slack channel specified.\nSkipping sending message to Slack."
            )
            return
        text = (
            f"<{self._mention_to}>\n{data}"
            if self._mention_to
            and _LEVEL_ORDER[level] >= _LEVEL_ORDER[self._mention_level]
            else str(data)
        )
        self._client.chat_postMessage(
            text=text,
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

    def watch(self, label: str | None = None, *, channel: str | None = None) -> _Watch:
        return _Watch(
            partial(self._send, channel=channel),
            self._verbose,
            label,
        )
