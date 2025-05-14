from __future__ import annotations

from typing import Any

import requests

import notifyme._log as _log
from notifyme._base import _LEVEL_ORDER, _BaseNotifier, _LevelStr, _SendConfig


class DiscordNotifier(_BaseNotifier):
    platform = "Discord"

    def __init__(
        self,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not self._disable:
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
        level: _LevelStr = "info",
    ) -> None:
        channel_id = send_config.channel or self._default_channel
        if not channel_id:
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
            if mention_to and _LEVEL_ORDER[level] >= _LEVEL_ORDER[mention_level]
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
