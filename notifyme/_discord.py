import os
from functools import partial
from typing import Any

import requests

import notifyme._log as _log
from notifyme._base import _LEVEL_ORDER, _BaseNotifier, _LevelStr, _Watch


class DiscordNotifier(_BaseNotifier):
    platform = "Discord"

    def __init__(
        self,
        verbose: bool = True,
        mention_to: str | None = None,
        mention_level: _LevelStr = "error",
        channel_id: str | None = None,
        discord_token: str | None = None,
        disable: bool = False,
    ) -> None:
        super().__init__(verbose, mention_to, mention_level, disable)
        self._default_channel_id = channel_id
        self._token = discord_token or os.getenv("DISCORD_BOT_TOKEN")
        if not self._disable:
            if channel_id:
                _log.info(f"DiscordNotifier initialized with channel ID: {channel_id}")
            else:
                _log.warn(
                    "No Discord channel ID configured. Need to specify channel each time."
                )

    def _do_send(
        self,
        data: Any,
        tb: str | None = None,
        level: _LevelStr = "info",
        *,
        channel_id: str | None = None,
    ) -> None:
        channel_id = channel_id or self._default_channel_id
        if not channel_id:
            _log.error(
                "No Discord channel ID specified.\nSkipping sending message to Discord."
            )
            return
        headers = {
            "Authorization": f"Bot {self._token}",
            "Content-Type": "application/json",
        }
        text = (
            f"<{self._mention_to}>\n{data}"
            if self._mention_to
            and _LEVEL_ORDER[level] >= _LEVEL_ORDER[self._mention_level]
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

    def watch(
        self,
        label: str | None = None,
        *,
        channel_id: str | None = None,
    ) -> _Watch:
        return _Watch(
            partial(self._send, channel_id=channel_id),
            self._verbose,
            label,
        )
