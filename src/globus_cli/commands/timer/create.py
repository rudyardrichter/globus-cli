import datetime
from enum import Enum
from typing import List, Optional, Tuple, cast

import click
from globus_sdk import TimerJob, TransferData

from globus_cli.commands.transfer import autoactivate
from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command, group, mutex_option_group
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print

from ._common import (
    DATETIME_FORMATS,
    JOB_FORMAT_FIELDS,
    START_HELP,
    parse_timedelta,
    read_csv,
)

INTERVAL_HELP = """
    Interval at which the job should run. Use 'w', 'd', 'h', 'm', and 's' as suffixes
    to specify weeks, days, hours, minutes, and seconds. Examples: '1h 30m', '500s',
    '24h', '1d 12h', '2w', etc. Must be in order: hours -> minutes -> seconds. You
    should either use quotes ('1d 2h') or write without spaces (1d2h).
"""


class SyncLevel(Enum):
    exists = 0
    size = 1
    mtime = 2
    checksum = 3


@group("create", short_help="Submit a Timer job", hidden=True)
def create_command():
    pass


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
    default=None,
    type=click.Choice(("exists", "size", "mtime", "checksum"), case_sensitive=False),
    help=(
        "Specify that only new or modified files should be transferred, depending on"
        " which setting is provided"
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
    sync_level: Optional[str],
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
    """
    Create a Timer job which will run a transfer on a recurring schedule
    according to the parameters provided.
    """
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
    # required to suppress language server errors for some reason?
    assert transfer_client.scopes is not None

    # Check endpoint activation, figure out scopes needed.
    for ep in [source_endpoint, dest_endpoint]:
        # Note this will provide help text on activating endpoints.
        autoactivate(transfer_client, ep, if_expires_in=86400)

    # FOR NOW: we will only ask for the basic transfer action provider scope, and ignore
    # anything to do with the endpoints themselves.
    scope = "https://auth.globus.org/scopes/actions.globus.org/transfer/transfer"
    login_manager.run_login_flow(scopes=[str(scope)])
    sync_level_int = None
    if sync_level:
        sync_level_int = SyncLevel[sync_level].value

    transfer_data = TransferData(
        transfer_client,
        source_endpoint,
        dest_endpoint,
        label=label,
        sync_level=sync_level_int,
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
        fieldnames = ["source_path", "destination_path", "recursive"]
        for row in read_csv(items_file, fieldnames):
            transfer_data.add_item(
                cast(str, row["source_path"]),
                cast(str, row["destination_path"]),
                recursive=cast(bool, row["recursive"]),
            )
    if not transfer_data.items:
        raise click.UsageError(
            "either --items-file or one or more --item options must be provided"
        )

    start_with_tz = start or datetime.datetime.now()
    if start_with_tz.tzinfo is None:
        start_with_tz = start_with_tz.astimezone()
    response = timer_client.create_job(
        TimerJob.from_transfer_data(
            transfer_data,
            start_with_tz,
            interval_seconds,
            name=name,
            stop_after=stop_after_date,
            stop_after_n=stop_after_runs,
            scope=str(scope),
        )
    )
    formatted_print(response, text_format=FORMAT_TEXT_RECORD, fields=JOB_FORMAT_FIELDS)


create_command.add_command(transfer)
