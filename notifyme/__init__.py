from notifyme._core import init, send, watch
from notifyme._discord import DiscordNotifier
from notifyme._slack import SlackNotifier

__all__ = [
    "DiscordNotifier",
    "SlackNotifier",
    "init",
    "send",
    "watch",
]

__version__ = "0.1.0"
