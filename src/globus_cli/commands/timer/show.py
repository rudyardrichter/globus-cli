import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print
from ._common import JOB_FORMAT_FIELDS


@command("show", short_help="Display information about a particular job")
@click.argument("JOB_ID")
@LoginManager.requires_login(LoginManager.TIMER_RS)
def show_command(login_manager: LoginManager, job_id: str):
    """
    TODO
    """
    timer_client = login_manager.get_timer_client()
    response = timer_client.get_job(job_id)
    formatted_print(response, text_format=FORMAT_TEXT_RECORD, fields=JOB_FORMAT_FIELDS)
