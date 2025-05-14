from __future__ import annotations

import sys
from contextlib import ContextDecorator
from typing import Any

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

import pytest

from notifyme._core import _DESTINATIONS, _combine_contexts, allow_multi_dest


@allow_multi_dest
def dummy_send(
    send_to: _DESTINATIONS | list[_DESTINATIONS] | None = None, **kwargs: Any
) -> None:
    return None


@pytest.mark.parametrize(
    "send_to",
    [
        None,
        "slack",
        ["slack", "discord"],
    ],
)
def test_allow_multi_dest(send_to: _DESTINATIONS | list[_DESTINATIONS]) -> None:
    assert dummy_send(send_to=send_to) is None


def test_wo_specify_dest() -> None:
    assert dummy_send() is None


def test_combine_contexts_order() -> None:
    called = []

    class A(ContextDecorator):
        def __enter__(self) -> Self:
            called.append("A+")
            return self

        def __exit__(self, *e: Any) -> None:
            called.append("A-")

    class B(ContextDecorator):
        def __enter__(self) -> Self:
            called.append("B+")
            return self

        def __exit__(self, *e: Any) -> None:
            called.append("B-")

    combo = _combine_contexts([A(), B()])  # type: ignore
    with combo:
        called.append("BODY")
    assert called == ["A+", "B+", "BODY", "B-", "A-"]
