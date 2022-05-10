import datetime
import re
import sys
from csv import DictReader
from distutils.util import strtobool
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Tuple, Union
from urllib.parse import urlparse

import click

from globus_sdk import GlobusError, GlobusHTTPResponse, TransferClient
from globus_cli.termio import is_verbose


def _get_stop_date(data: Dict[str, Any]) -> Optional[str]:
    if not data["stop_after"]:
        return None
    return data.get("stop_after", {}).get("date")


def _get_stop_n_runs(data: Dict[str, Any]) -> Optional[str]:
    if not data["stop_after"]:
        return None
    return data.get("stop_after", {}).get("n_runs")


def _get_action_type(data: Dict[str, Any]) -> str:
    url = urlparse(data["callback_url"])
    if url.netloc.endswith("actions.automate.globus.org") and url.path == "/transfer/transfer/run":
        return "Transfer"
    if url.netloc.endswith("flows.automate.globus.org"):
        return "Flow"
    else:
        return data["callback_url"]


def _get_interval(data: Dict[str, Any]) -> Optional[str]:
    if not data["interval"]:
        return None
    return str(datetime.timedelta(seconds=data["interval"]))


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

# List of datetime formats accepted as input. (`%z` means timezone.)
DATETIME_FORMATS = [
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S%z",
]


timedelta_regex = re.compile(
    r"\s*((?P<weeks>\d+)w)?"
    r"\s*((?P<days>\d+)d)?"
    r"\s*((?P<hours>\d+)h)?"
    r"\s*((?P<minutes>\d+)m)?"
    r"\s*((?P<seconds>\d+)s?)?"
)


def isoformat_to_local(utc_str: Optional[str]) -> Optional[str]:
    if not utc_str:
        return None
    date = datetime.datetime.fromisoformat(utc_str)
    import pdb; pdb.set_trace()
    if date.tzinfo is None:
        return date.strftime("%Y-%m-%d %H:%M")
    return date.astimezone(tz=None).strftime("%Y-%m-%d %H:%M")


def get_required_data_access_scopes(
    tc: TransferClient,
    collection_ids: Iterable[str],
) -> List[str]:
    data_access_scopes: List[str] = []
    for collection_id in collection_ids:
        collection_id_info = tc.get_endpoint(collection_id)
        if collection_id_info["DATA_TYPE"] == "endpoint":
            gcs_version = collection_id_info.get("gcs_version")
            if gcs_version is None:
                continue
            gcs_version_parts = [int(x) for x in gcs_version.split(".")]
            requires_data_access = all(
                [
                    (
                        gcs_version_parts[0] > 5
                        or (gcs_version_parts[0] == 5 and gcs_version_parts[1] >= 4),
                    ),
                    (collection_id_info.get("high_assurance", True) is False),
                    collection_id_info.get("host_endpoint", True) is None,
                ]
            )
            if requires_data_access:
                data_access_scopes.append(
                    f"https://auth.globus.org/scopes/{collection_id}/data_access"
                )
    return data_access_scopes


def parse_timedelta(s: str) -> datetime.timedelta:
    groups = {k: int(v) for k, v in timedelta_regex.match(s).groupdict(0).items()}
    # timedelta accepts kwargs for units up through days, have to convert weeks
    groups["days"] += groups.pop("weeks", 0) * 7
    return datetime.timedelta(**groups)


def read_csv(
    file_name: str,
    fieldnames=["source_path", "destination_path", "recursive"],
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

    with open(file_name, "r") as f:
        reader = DictReader(decomment(f), fieldnames=fieldnames)
        for row_dict in reader:
            yield {k: transform_val(k, v) for k, v in row_dict.items()}


def require_activated_endpoints(
    transfer_client: TransferClient,
    endpoints: List[str],
    reactivate_if_expires_in: int = 86400,
):
    not_activated = []
    for endpoint in endpoints:
        try:
            if not transfer_client.get_endpoint(endpoint).get("activated"):
                not_activated.append(endpoint)
        except GlobusError as e:
            err_msg = "couldn't get information for endpoint {endpoint}"
            code = getattr(e, "code", None)
            msg = getattr(e, "message", None)
            if code and msg:
                err_msg += f": {code} {msg}"
            click.echo(err_msg, err=True)
            sys.exit(1)
    still_not_activated = []
    for endpoint in not_activated:
        response = transfer_client.endpoint_autoactivate(
            endpoint, if_expires_in=reactivate_if_expires_in
        )
        if response.get("code") == "AutoActivationFailed":
            still_not_activated.append(endpoint)
    if still_not_activated:
        show_endpoints = ", ".join(still_not_activated)
        click.echo(
            f"Error: requested endpoint is not activated: {show_endpoints}\n"
            "Open in the web app to activate:",
            err=True,
        )
        for endpoint in still_not_activated:
            click.echo(
                f"    https://app.globus.org/file-manager?origin_id={endpoint}",
                err=True,
            )
        sys.exit(1)
