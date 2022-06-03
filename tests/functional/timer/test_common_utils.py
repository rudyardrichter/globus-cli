from datetime import timedelta, timezone, tzinfo
from typing import Optional

import pytest

from globus_cli.commands.timer._common import isoformat_to_local


@pytest.mark.parametrize(
    "utc_str, localtz, output",
    [
        (
            "2022-01-01T12:00:00+00:00",
            timezone(offset=timedelta(hours=-5)),
            "2022-01-01 07:00",
        ),
        (
            "2022-01-01T12:00:00Z",
            timezone(offset=timedelta(hours=-5)),
            "2022-01-01 07:00",
        ),
        (
            "2022-01-01T12:00:00+00:00",
            timezone(offset=timedelta(hours=4)),
            "2022-01-01 16:00",
        ),
        (
            "2022-01-01T12:00:00Z",
            timezone(offset=timedelta(hours=4)),
            "2022-01-01 16:00",
        ),
    ],
)
def test_isoformat_to_local(
    utc_str: str, localtz: Optional[tzinfo], output: Optional[str]
):
    assert isoformat_to_local(utc_str, localtz=localtz) == output
