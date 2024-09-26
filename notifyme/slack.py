from __future__ import annotations

import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()
_client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))

def send_to_slack(
    channel: str,
    text: str,
    blocks: list | None = None,
    attachments: list | None = None,
) -> None:
    try:
        _client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks,
            attachments=attachments,
        )
    except SlackApiError as e:
        print(f"Error posting to Slack: {e}")