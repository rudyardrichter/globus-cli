import datetime
import re
from typing import Any, Dict, Optional, cast
from urllib.parse import urlparse

import click

# List of datetime formats accepted as input. (`%z` means timezone.)
DATETIME_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
]


def _get_stop_date(data: Dict[str, Any]) -> Optional[str]:
    if not data["stop_after"]:
        return None
    return str(data.get("stop_after", {}).get("date"))


def _get_stop_n_runs(data: Dict[str, Any]) -> Optional[str]:
    if not data["stop_after"]:
        return None
    return str(data.get("stop_after", {}).get("n_runs"))


def _get_action_type(data: Dict[str, Any]) -> str:
    url = urlparse(data["callback_url"])
    if (
        url.netloc.endswith("actions.automate.globus.org")
        and url.path == "/transfer/transfer/run"
    ):
        return "Transfer"
    if url.netloc.endswith("flows.automate.globus.org"):
        return "Flow"
    else:
        return str(data["callback_url"])


def _get_interval(data: Dict[str, Any]) -> Optional[str]:
    if not data["interval"]:
        return None
    return str(datetime.timedelta(seconds=data["interval"]))


def isoformat_to_local(utc_str: Optional[str]) -> Optional[str]:
    if not utc_str:
        return None
    date = click.DateTime(formats=DATETIME_FORMATS)(utc_str)
    if date.tzinfo is None:
        return cast(str, date.strftime("%Y-%m-%d %H:%M"))
    return cast(str, date.astimezone(tz=None).strftime("%Y-%m-%d %H:%M"))


JOB_FORMAT_FIELDS = [
    ("Job ID", "job_id"),
    ("Name", "name"),
    ("Type", _get_action_type),
    ("Submitted At", lambda data: isoformat_to_local(data["submitted_at"])),
    ("Start", lambda data: isoformat_to_local(data["start"])),
    ("Interval", _get_interval),
    ("Last Run", lambda data: isoformat_to_local(data["last_ran_at"])),
    ("Next Run", lambda data: isoformat_to_local(data["next_run"])),
    ("Stop After Date", _get_stop_date),
    ("Stop After N. Runs", _get_stop_n_runs),
    ("N. Runs", lambda data: data["n_runs"]),
    ("N. Timer Errors", lambda data: data["n_errors"]),
]

START_HELP = """
Start time for the job. Defaults to current time. (The example above shows the allowed
formats using Python's datetime formatters; see:
https://docs.python.org/3/library/datetime.html #strftime-and-strptime-format-codes
"""

timedelta_regex = re.compile(
    r"\s*((?P<weeks>\d+)w)?"
    r"\s*((?P<days>\d+)d)?"
    r"\s*((?P<hours>\d+)h)?"
    r"\s*((?P<minutes>\d+)m)?"
    r"\s*((?P<seconds>\d+)s?)?"
)
