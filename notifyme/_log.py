from datetime import datetime
from enum import Enum


class _LogColor(Enum):
    RESET = "\033[0m"
    BOLD = "\033[01m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


_PREFIX = "[notifyme] "


def info(message: str, with_timestamp: bool = True) -> None:
    _print_with_prefix(
        message,
        prefix_color=_LogColor.CYAN,
        time_color=_LogColor.BLUE,
        with_timestamp=with_timestamp,
    )


def error(message: str, with_timestamp: bool = True) -> None:
    _print_with_prefix(
        message,
        prefix_color=_LogColor.RED,
        time_color=_LogColor.MAGENTA,
        with_timestamp=with_timestamp,
    )


def _print_with_prefix(
    message: str,
    prefix_color: _LogColor,
    time_color: _LogColor,
    with_timestamp: bool = True,
) -> None:
    prefix = f"{prefix_color.value}{_PREFIX}{_LogColor.RESET.value}"
    prefix = (
        f"{prefix}{time_color.value}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {_LogColor.RESET.value}"
        if with_timestamp
        else prefix
    )
    message = "\n".join([prefix + line for line in message.splitlines()])
    print(message)
