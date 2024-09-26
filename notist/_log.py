from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    if sys.version_info >= (3, 11):
        from typing import Self
    else:
        from typing_extensions import Self


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
    prefix = f"{prefix_color}{_PREFIX}{level_str}{RESET}"
    prefix = (
        f"{prefix}{time_color}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {RESET}"
        if with_timestamp
        else prefix
    )
    message = "\n".join([prefix + line for line in message.splitlines()])
    print(_prepare_for_console(message))


_CSI = "\x1b["
RESET = f"{_CSI}0m"


def fg16(code: int) -> str:
    return f"{_CSI}{code}m"


def fg256(n: int) -> str:
    return f"{_CSI}38;5;{n}m"


# NOTE: Python 3.11+ introduces enum.StrEnum.
# After dropping Python 3.10 support, switch to stdlib StrEnum and remove the shim.
# See:
#   - https://docs.python.org/3/library/enum.html#enum.StrEnum
#   - https://docs.python.org/3.11/whatsnew/3.11.html
class Glyph(str, Enum):
    TL, TR, BL, BR = "╭", "╮", "╰", "╯"
    H, V, SEP_L, SEP_R, SEP_T, SEP_B = "─", "│", "├", "┤", "┬", "┴"
    BH = "━"
    TDH, BTDH, QDH, BQDH = "┄", "┅", "┈", "┉"
    RARROW, LARROW = "▶", "◀"
    RARROWF, LARROWF = "▷", "◁"
    RARROWP = "❯"
    BULLET, WBULLET, CBULLET = "•", "◦", "⦿"
    CHECK, CROSS = "✓", "✗"
    WARN, INFO = "⚠", "ℹ"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class _Expansion:
    placeholder: str
    console: str
    message: str


class SpecialToken(str, Enum):
    def __new__(cls, expansion: _Expansion) -> Self:
        obj = str.__new__(cls, expansion.placeholder)
        obj._value_ = expansion.placeholder
        obj._console = expansion.console  # type: ignore[attr-defined]
        obj._message = expansion.message  # type: ignore[attr-defined]
        return obj

    BT_CON = _Expansion("<|@BACKTICK::CONSOLE|>", "`", "")
    BT_MSG = _Expansion("<|@BACKTICK::MESSAGE|>", "", "`")
    BT_ALW = _Expansion("<|@BACKTICK::ALWAYS|>", "`", "`")
    FNO_CON = _Expansion("<|@FENCE!OPEN::CONSOLE|>", "```\n", "")
    FNC_CON = _Expansion("<|@FENCE!CLOSE::CONSOLE|>", "\n```", "")
    FNO_MSG = _Expansion("<|@FENCE!OPEN::MESSAGE|>", "", "```\n")
    FNC_MSG = _Expansion("<|@FENCE!CLOSE::MESSAGE|>", "", "\n```")
    FNO_ALW = _Expansion("<|@FENCE!OPEN::ALWAYS|>", "```\n", "```\n")
    FNC_ALW = _Expansion("<|@FENCE!CLOSE::ALWAYS|>", "\n```", "\n```")

    def __str__(self) -> str:
        return self.value


def _expand_special_tokens(text: str, target: Literal["console", "message"]) -> str:
    for token in SpecialToken:
        replacement = token._console if target == "console" else token._message  # type: ignore[attr-defined]
        text = text.replace(token.value, replacement)
    return text


def _strip_sgr(text: str) -> str:
    """Remove ANSI SGR sequences (ESC[ ... m)."""
    return re.compile(r"\x1b\[[0-9;]*m").sub("", text)


def _prepare_for_console(text: str) -> str:
    return _expand_special_tokens(text, target="console")


def prepare_for_message(text: str) -> str:
    text = _expand_special_tokens(text, target="message")
    return _strip_sgr(text)
