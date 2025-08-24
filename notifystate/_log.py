from __future__ import annotations

from datetime import datetime
from typing import Literal

_PREFIX = "[NotifyState] "


# NOTE: Python 3.12+ (PEP 695) supports type statement.
# After dropping Python 3.11 support, update this to use that instead.
# See:
#   - https://peps.python.org/pep-0695/
#   - https://docs.python.org/3/library/typing.html#type-aliases
LevelStr = Literal["info", "warning", "error"]
LEVEL_ORDER: dict[LevelStr, int] = {
    "info": 0,
    "warning": 1,
    "error": 2,
}


def info(message: str, with_timestamp: bool = True) -> None:
    _print_with_prefix(
        message,
        level_str="[INFO] ",
        prefix_color=fg256(48),
        time_color=fg256(14),
        with_timestamp=with_timestamp,
    )


def warn(message: str, with_timestamp: bool = True) -> None:
    _print_with_prefix(
        message,
        level_str="[WARN] ",
        prefix_color=fg256(214),
        time_color=fg16(93),
        with_timestamp=with_timestamp,
    )


def error(message: str, with_timestamp: bool = True) -> None:
    _print_with_prefix(
        message,
        level_str="[ERROR] ",
        prefix_color=fg256(196),
        time_color=fg256(213),
        with_timestamp=with_timestamp,
    )


def _print_with_prefix(
    message: str,
    level_str: str,
    prefix_color: str,
    time_color: str,
    with_timestamp: bool = True,
) -> None:
    prefix = f"{prefix_color}{_PREFIX}{level_str}{_RESET}"
    prefix = (
        f"{prefix}{time_color}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {_RESET}"
        if with_timestamp
        else prefix
    )
    message = "\n".join([prefix + line for line in message.splitlines()])
    print(message)


_CSI = "\x1b["
_RESET = f"{_CSI}0m"


def fg16(code: int) -> str:
    return f"{_CSI}{code}m"


def fg256(n: int) -> str:
    return f"{_CSI}38;5;{n}m"


_TL, _TR, _BL, _BR = "╭", "╮", "╰", "╯"
_H, _V, _SEP_L, _SEP_R, _SEP_T, _SEP_B = "─", "│", "├", "┤", "┬", "┴"
_BH = "━"
_TDH, _BTDH, _QDH, _BQDH = "┄", "┅", "┈", "┉"
_RARROW, _LARROW = "▶", "◀"
_RARROWF, _LARROWF = "▷", "◁"
_RARROWP = "❯"
_BULLET, _WBULLET, _CBULLET = "•", "◦", "⦿"
