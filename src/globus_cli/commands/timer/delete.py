import uuid
from typing import Iterable

import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import FORMAT_TEXT_RECORD_LIST, formatted_print

from ._common import DELETED_JOB_FORMAT_FIELDS


@command("delete", short_help="Delete one or more jobs", hidden=True)
@click.argument("JOB_IDS", type=uuid.UUID, nargs=-1)
@LoginManager.requires_login(LoginManager.TIMER_RS)
def delete_command(login_manager: LoginManager, job_ids: Iterable[uuid.UUID]):
    """
    Delete one or more Timer jobs.

    The contents of the deleted jobs are printed afterwards. If multiple jobs are
    deleted, the contents of each are printed separated by blank lines.
    """
    timer_client = login_manager.get_timer_client()
    first = True
    for job_id in job_ids:
        deleted = timer_client.delete_job(job_id)
        if first:
            first = False
        else:
            click.echo()
        formatted_print(
            deleted,
            text_format=FORMAT_TEXT_RECORD_LIST,
            fields=DELETED_JOB_FORMAT_FIELDS,
        )
