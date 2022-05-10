import datetime
from typing import List, Optional, Tuple, cast

import click
from globus_sdk import TimerJob, TransferData
from globus_sdk.scopes import MutableScope, TransferScopes

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command, group, mutex_option_group
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print

from ._common import DATETIME_FORMATS, JOB_FORMAT_FIELDS, START_HELP, get_required_data_access_scopes, parse_timedelta, read_csv, require_activated_endpoints


INTERVAL_HELP = """
    Interval at which the job should run. Use 'w', 'd', 'h', 'm', and 's' as suffixes
    to specify weeks, days, hours, minutes, and seconds. Examples: '1h 30m', '500s',
    '24h', '1d 12h', '2w', etc. Must be in order: hours -> minutes -> seconds. You
    should either use quotes ('1d 2h') or write without spaces (1d2h).
"""


@command("transfer", short_help="Create a recurring transfer job in Timer")
@click.option(
    "--name",
    required=True,
    type=str,
    help="Name to identify this job in the timer service (not necessarily unique)",
)
@click.option(
    "--start",
    required=False,
    type=click.DateTime(formats=DATETIME_FORMATS),
    help=START_HELP,
)
@click.option(
    "--interval",
    required=False,
    type=str,
    help=INTERVAL_HELP,
)
@click.option(
    "--source-endpoint",
    required=True,
    type=str,
    help="ID for the source transfer endpoint",
)
@click.option(
    "--dest-endpoint",
    required=True,
    type=str,
    help="ID for the destination transfer endpoint",
)
@click.option(
    "--label",
    required=False,
    type=str,
    help=(
        "An optional label for the transfer operation, up to 128 characters long. Must"
        " contain only letters/numbers/spaces, and the following characters: - _ ,"
    ),
)
@click.option(
    "--stop-after-date",
    required=False,
    type=click.DateTime(formats=DATETIME_FORMATS),
    help=("Stop running the transfer after this date"),
)
@click.option(
    "--stop-after-runs",
    required=False,
    type=int,
    help=("Stop running the transfer after this number of runs have happened"),
)
@click.option(
    "--sync-level",
    required=False,
    type=int,
    help=(
        "Specify that only new or modified files should be transferred. The behavior"
        " depends on the value of this parameter, which must be a value 0–3, as"
        " defined in the transfer API: 0. Copy files that do not exist at the"
        " destination. 1. Copy files if the size of the destination does not match the"
        " size of the source. 2. Copy files if the timestamp of the destination is"
        " older than the timestamp of the source. 3. Copy files if checksums of the"
        " source and destination do not match."
    ),
)
@click.option(
    "--encrypt-data",
    is_flag=True,
    default=False,
    help="Whether Transfer should encrypt data sent through the network using TLS",
)
@click.option(
    "--verify-checksum",
    is_flag=True,
    default=False,
    help=(
        "Whether Transfer should verify file checksums and retry if the source and"
        " destination don't match"
    ),
)
@click.option(
    "--preserve-timestamp",
    is_flag=True,
    default=False,
    help=(
        "Whether Transfer should set file timestamps on the destination to match the"
        " origin"
    ),
)
@click.option(
    "--item",
    "-i",
    required=False,
    type=(str, str, bool),
    multiple=True,
    help=(
        "Used to specify the transfer items; provide as many of this option as files"
        " to transfer. The format for this option is `--item SRC DST RECURSIVE`, where"
        " RECURSIVE specifies, if this item is a directory, to transfer the entire"
        " directory. For example: `--item ~/file1.txt ~/new_file1.txt false`"
    ),
)
@click.option(
    "--skip-source-errors",
    is_flag=True,
    default=False,
    help=(
        "Skip files or directories on the source endpoint that hit PERMISSION_DENIED or"
        " FILE_NOT_FOUND errors."
    ),
)
@click.option(
    "--fail-on-quota-errors",
    is_flag=True,
    default=False,
    help="Cancel the submitted transfer tasks if QUOTA_EXCEEDED errors are hit.",
)
@click.option(
    "--recursive-symlinks",
    required=False,
    type=click.Choice(["ignore", "keep", "copy"], case_sensitive=False),
    default="ignore",
)
@click.option(
    "--items-file",
    required=False,
    type=str,
    help="file containing table of items to transfer",
)
@click.option(
    "--notify-on-succeeded",
    is_flag=True,
    default=True,
    help="Send notification email on task success",
)
@click.option(
    "--notify-on-failed",
    is_flag=True,
    default=True,
    help="Send notification email on task failure",
)
@click.option(
    "--notify-on-inactive",
    is_flag=True,
    default=True,
    help="Send notification email on task becoming inactive",
)
@mutex_option_group("--action-file", "--action-body")
@LoginManager.requires_login(LoginManager.TIMER_RS, LoginManager.TRANSFER_RS)
def transfer(
    login_manager: LoginManager,
    name: str,
    item: List[Tuple[str, str, bool]],
    items_file: Optional[str],
    start: Optional[datetime.datetime],
    interval: Optional[str],
    source_endpoint: str,
    dest_endpoint: str,
    label: Optional[str],
    stop_after_date: Optional[datetime.datetime],
    stop_after_runs: Optional[int],
    sync_level: Optional[int],
    encrypt_data: bool,
    verify_checksum: bool,
    preserve_timestamp: bool,
    skip_source_errors: bool,
    fail_on_quota_errors: bool,
    recursive_symlinks: str,
    notify_on_succeeded: bool,
    notify_on_failed: bool,
    notify_on_inactive: bool,
):
    # Interval must be null iff the job is non-repeating, i.e. stop-after-runs == 1.
    if stop_after_runs != 1:
        if interval is None:
            raise click.UsageError("Missing option '--interval'.")
    # More input validation
    if interval is not None:
        try:
            interval_seconds = int(parse_timedelta(interval).total_seconds())
        except TypeError:
            raise click.UsageError(f"Couldn't parse interval: {interval}")
    else:
        interval_seconds = None

    timer_client = login_manager.get_timer_client()
    transfer_client = login_manager.get_transfer_client()
    # required to suppress errors for some reason?
    assert transfer_client.scopes is not None

    # Check endpoint activation, figure out scopes needed
    endpoints = [source_endpoint, dest_endpoint]
    require_activated_endpoints(transfer_client, endpoints)
    scope = transfer_client.scopes.make_mutable("all")
    scope = MutableScope(
        "https://auth.globus.org/scopes/actions.globus.org/transfer/transfer"
    )
    scope.add_dependency(transfer_client.scopes.all)
    data_access_scopes = get_required_data_access_scopes(transfer_client, endpoints)
    for data_access_scope in data_access_scopes:
        scope.add_dependency(data_access_scope)
    import pdb; pdb.set_trace()
    login_manager.run_login_flow(scopes=[str(scope)])

    transfer_data = TransferData(
        transfer_client,
        source_endpoint,
        dest_endpoint,
        label=label,
        sync_level=sync_level,
        verify_checksum=verify_checksum,
        preserve_timestamp=preserve_timestamp,
        encrypt_data=encrypt_data,
        skip_source_errors=skip_source_errors,
        fail_on_quota_errors=fail_on_quota_errors,
        recursive_symlinks=recursive_symlinks,
        notify_on_succeeded=notify_on_succeeded,
        notify_on_failed=notify_on_failed,
        notify_on_inactive=notify_on_inactive,
    )

    if item:
        for i in item:
            transfer_data.add_item(i[0], i[1], recursive=i[2])
    if items_file:
        for i in read_csv(items_file):
            transfer_data.add_item(cast(str, i["source_path"]), cast(str, i["destination_path"]), recursive=cast(bool, i["recursive"]))
    if not transfer_data.items:
        raise click.UsageError(
            "either --items-file or one or more --item options must be provided"
        )

    start_with_tz = start or datetime.datetime.now()
    if start_with_tz.tzinfo is None:
        start_with_tz = start_with_tz.astimezone()
    response = timer_client.create_job(TimerJob.from_transfer_data(
        transfer_data, start_with_tz, interval_seconds, name=name,
        stop_after=stop_after_date, stop_after_n=stop_after_runs, scope=str(scope),
    ))
    formatted_print(response, text_format=FORMAT_TEXT_RECORD, fields=JOB_FORMAT_FIELDS)


@group("create", short_help="Submit a Timer job")
def create_command():
    pass


create_command.add_command(transfer)
