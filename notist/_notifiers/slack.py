from __future__ import annotations

from typing import TYPE_CHECKING

from slack_sdk import WebClient

from notist import _log
from notist._log import LEVEL_ORDER, RESET, fg256
from notist._notifiers.base import (
    DOC_ADDITIONS_BASE,
    BaseNotifier,
    _SendConfig,
)
from notist._utils import extend_method_docstring

if TYPE_CHECKING:
    from notist._log import LevelStr


_DOC_ADDITIONS = {
    "__init__": """
        Example:

            .. code-block:: python

               from notist import SlackNotifier

               # Create a SlackNotifier with defaults
               slack = SlackNotifier(
                   channel="my-channel",  # Slack channel name or ID
                   mention_to="@U012345678",  # Mention a specific user (Optional)
               )
        """,
}


@extend_method_docstring(_DOC_ADDITIONS | DOC_ADDITIONS_BASE)
class SlackNotifier(BaseNotifier):
    _platform = "Slack"

    def __init__(
        self,
        channel: str | None = None,
        mention_to: str | None = None,
        mention_level: LevelStr = "error",
        mention_if_ends: bool = True,
        callsite_level: LevelStr = "error",
        token: str | None = None,
        verbose: bool = True,
        disable: bool = False,
    ) -> None:
        super().__init__(
            channel,
            mention_to,
            mention_level,
            mention_if_ends,
            callsite_level,
            token,
            verbose,
            disable,
        )
        self._client = WebClient(token=self._token)
        if not self._disable and verbose:
            if self._default_channel:
                _log.info(
                    f"SlackNotifier initialized with default channel: {fg256(33)}{self._default_channel}{RESET}"
                )
            else:
                _log.warn(
                    "No Slack channel configured. Need to specify channel each time."
                )

    def _do_send(
        self,
        send_config: _SendConfig,
        message: str,
        tb: str | None = None,
        level: LevelStr = "info",
    ) -> None:
        channel = send_config.channel or self._default_channel
        if channel is None:
            if send_config.verbose:
                _log.error(
                    "No Slack channel specified.\nSkipping sending message to Slack."
                )
            return
        mention_to = send_config.mention_to or self._mention_to
        mention_level = send_config.mention_level or self._mention_level
        text = (
            f"<{mention_to}>\n{message}"
            if mention_to
            and LEVEL_ORDER[level] >= LEVEL_ORDER[mention_level]
            or (send_config.mention_if_ends and "End" in message)
            else message
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
