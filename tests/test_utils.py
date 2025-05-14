from datetime import timedelta

import pytest

from notifyme._utils import format_timedelta


@pytest.mark.parametrize(
    "delta, expected",
    [
        (timedelta(seconds=3), "3s"),
        (timedelta(minutes=2, seconds=3), "2m 3s"),
        (timedelta(hours=1), "1h"),
        (timedelta(days=2, hours=1), "2d 1h"),
        (timedelta(), "0s"),
    ],
)
def test_format_timedelta(delta: timedelta, expected: str) -> None:
    assert format_timedelta(delta) == expected
