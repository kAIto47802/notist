from __future__ import annotations

from typing import Any

import requests

import notifystate._log as _log
from notifystate._log import LEVEL_ORDER, LevelStr
from notifystate._notifiers.base import (
    DOC_ADDITIONS_BASE,
    BaseNotifier,
    _SendConfig,
)
from notifystate._utils import extend_method_docstring

_DOC_ADDITIONS = {
    "__init__": """
        Example:

            .. code-block:: python

               from notifystate import DiscordNotifier

               # Create a DiscordNotifier with defaults
               discord = DiscordNotifier(
                   channel="1234567890123456789",  # Discord channel ID (cannot use channel name for Discord)
                   mention_to="@U012345678",  # Mention a specific user (Optional)
               )
        """,
}


@extend_method_docstring(_DOC_ADDITIONS | DOC_ADDITIONS_BASE)
class DiscordNotifier(BaseNotifier):
    _platform = "Discord"

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
        if not self._disable and self._verbose:
            if self._default_channel:
                _log.info(
                    f"DiscordNotifier initialized with channel ID: {self._default_channel}"
                )
            else:
                _log.warn(
                    "No Discord channel ID configured. Need to specify channel each time."
                )

    def _do_send(
        self,
        data: Any,
        send_config: _SendConfig,
        tb: str | None = None,
        level: LevelStr = "info",
    ) -> None:
        channel_id = send_config.channel or self._default_channel
        if not channel_id and self._verbose:
            _log.error(
                "No Discord channel ID specified.\nSkipping sending message to Discord."
            )
            return
        headers = {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
        }
        mention_to = send_config.mention_to or self._mention_to
        mention_level = send_config.mention_level or self._mention_level
        text = (
            f"<{mention_to}>\n{data}"
            if mention_to and LEVEL_ORDER[level] >= LEVEL_ORDER[mention_level]
            else str(data)
        )
        payload: dict[str, Any] = {
            "content": text,
            "allowed_mentions": {"parse": ["users", "roles", "everyone"]},
        }
        if tb:
            payload["embeds"] = [{"description": tb, "color": 0xFF3D33}]

        resp = requests.post(
            f"https://discord.com/api/v10/channels/{channel_id}/messages",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
