from __future__ import annotations

from typing import Any

from slack_sdk import WebClient

import notifyend._log as _log
from notifyend._base import _LEVEL_ORDER, BaseNotifier, _LevelStr, _SendConfig


class SlackNotifier(BaseNotifier):
    platform = "Slack"

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._client = WebClient(token=self._token)
        if not self._disable:
            if self._default_channel:
                _log.info(
                    f"SlackNotifier initialized with default channel: {self._default_channel}"
                )
            else:
                _log.warn(
                    "No Slack channel configured. Need to specify channel each time."
                )

    def _do_send(
        self,
        data: Any,
        send_config: _SendConfig,
        tb: str | None = None,
        level: _LevelStr = "info",
    ) -> None:
        channel = send_config.channel or self._default_channel
        if channel is None:
            _log.error(
                "No Slack channel specified.\nSkipping sending message to Slack."
            )
            return
        mention_to = send_config.mention_to or self._mention_to
        mention_level = send_config.mention_level or self._mention_level
        text = (
            f"<{mention_to}>\n{data}"
            if mention_to and _LEVEL_ORDER[level] >= _LEVEL_ORDER[mention_level]
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
