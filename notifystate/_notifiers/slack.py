from __future__ import annotations

from typing import Any

from slack_sdk import WebClient

import notifystate._log as _log
from notifystate._notifiers.base import (
    _DOC_ADDITIONS_BASE,
    _LEVEL_ORDER,
    BaseNotifier,
    _LevelStr,
    _SendConfig,
)
from notifystate._utils import extend_method_docstring

_DOC_ADDITIONS = {
    "__init__": """
        Example:

            .. code-block:: python

               from notifystate import SlackNotifier

               # Create a SlackNotifier with defaults
               slack = SlackNotifier(
                   channel="my-channel",  # Slack channel name or ID
                   mention_to="@U012345678",  # Mention a specific user (Optional)
               )
        """,
}


@extend_method_docstring(_DOC_ADDITIONS | _DOC_ADDITIONS_BASE)
class SlackNotifier(BaseNotifier):
    _platform = "Slack"

    def __init__(
        self,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: _LevelStr = "error",
        mention_if_ends: bool = True,
        token: str | None = None,
        verbose: bool = True,
        disable: bool = False,
    ) -> None:
        super().__init__(
            channel,
            mention_to,
            mention_level,
            mention_if_ends,
            token,
            verbose,
            disable,
        )
        self._client = WebClient(token=self._token)
        if not self._disable and self._verbose:
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
        if channel is None and self._verbose:
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
