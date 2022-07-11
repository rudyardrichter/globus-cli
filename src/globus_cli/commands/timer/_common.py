import datetime
import re
import sys
from csv import DictReader
from distutils.util import strtobool
from typing import Any, Dict, Generator, List, Optional, Union
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


def isoformat_to_local(
    utc_str: Optional[str], localtz: Optional[datetime.tzinfo] = None
) -> Optional[str]:
    if not utc_str:
        return None
    # let this raise ValueError
    date = datetime.datetime.fromisoformat(utc_str)
    if date.tzinfo is None:
        return date.strftime("%Y-%m-%d %H:%M:%S")
    return date.astimezone(tz=localtz).strftime("%Y-%m-%d %H:%M:%S")


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

DELETED_JOB_FORMAT_FIELDS = [
    ("Job ID", "job_id"),
    ("Name", "name"),
    ("Type", _get_action_type),
    ("Submitted At", lambda data: isoformat_to_local(data["submitted_at"])),
    ("Start", lambda data: isoformat_to_local(data["start"])),
    ("Interval", _get_interval),
    ("Stop After Date", _get_stop_date),
    ("Stop After N. Runs", _get_stop_n_runs),
]

START_HELP = """
Start time for the job. Defaults to current time. (The example above shows the allowed
formats using Python's datetime formatters; see:
https://docs.python.org/3/library/datetime.html #strftime-and-strptime-format-codes
"""

timedelta_regex = re.compile(
    r"""
    ^
    ((?P<weeks>\d+)w)?
    ((?P<days>\d+)d)?
    ((?P<hours>\d+)h)?
    ((?P<minutes>\d+)m)?
    ((?P<seconds>\d+)s?)?
    $
    """,
    flags=re.VERBOSE,
)


def parse_timedelta(s: str) -> datetime.timedelta:
    matches = timedelta_regex.match(s)
    if not matches:
        raise ValueError(f"couldn't parse timedelta from string: {s}")
    return datetime.timedelta(**{k: int(v) for k, v in matches.groupdict(0).items()})


def read_csv(
    file_name: str,
    fieldnames: List[str],
    comment_char: str = "#",
) -> Generator[Dict[str, Union[str, bool]], None, None]:
    def decomment(f):
        for row in f:
            if not row.startswith(comment_char):
                yield row

    def transform_val(k: str, v: str) -> Union[str, bool]:
        v = v.strip()
        if k == "recursive":
            try:
                return bool(strtobool(v))
            except ValueError:
                # "invalid truth value"
                click.echo(f"In file {file_name}: couldn't parse {v} as a boolean")
                sys.exit(1)
        else:
            return v

    with open(file_name) as f:
        reader = DictReader(decomment(f), fieldnames=fieldnames)
        for row_dict in reader:
            yield {k: transform_val(k, v) for k, v in row_dict.items()}
