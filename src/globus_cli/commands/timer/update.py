import datetime
from typing import Optional

import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print
from ._common import DATETIME_FORMATS, JOB_FORMAT_FIELDS


@command("update", short_help="Modify a Timer job")
@LoginManager.requires_login(LoginManager.TIMER_RS)
@click.argument("JOB_ID")
@click.option(
    "--name",
    type=str,
    help="Name to identify this job in the timer service (not necessarily unique)",
)
@click.option(
    "--stop-after-date",
    type=click.DateTime(formats=DATETIME_FORMATS),
    help="Stop running the transfer after this date",
)
@click.option(
    "--stop-after-runs",
    type=int,
    help="Stop running the transfer after this number of runs have happened",
)
def update_command(
        login_manager: LoginManager, job_id: str, name: Optional[str], start: Optional[datetime.datetime], stop_after_date: Optional[datetime.datetime], stop_after_runs: Optional[int]):
    """
    Update certain parameters on an existing Timer job given its UUID.

    Start time and parameters such as transfer options cannot be changed once a job is
    submitted—only the name, interval, and stop conditions.
    """
    timer_client = login_manager.get_timer_client()
    data = {}
    if name:
        data["name"] = name
    if start:
        data["start"] = start
    if stop_after_date:
        data["stop_after"] = {"date": stop_after_date}
    if stop_after_runs:
        data["stop_after"] = {**data.get("stop_after"), "n_runs": stop_after_runs}
    formatted_print(
        timer_client.update_job(job_id, data),
        text_format=FORMAT_TEXT_RECORD,
        fields=JOB_FORMAT_FIELDS,
    )
