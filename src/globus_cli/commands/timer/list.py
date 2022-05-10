from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import FORMAT_TEXT_RECORD_LIST, formatted_print

from ._common import JOB_FORMAT_FIELDS


@command("list", short_help="List your jobs")
@LoginManager.requires_login(LoginManager.TIMER_RS)
def list_command(login_manager: LoginManager):
    """
    List your Timer jobs.
    """
    timer_client = login_manager.get_timer_client()
    response = timer_client.list_jobs(query_params={"order": "submitted_at asc"})
    formatted_print(
        response["jobs"],
        text_format=FORMAT_TEXT_RECORD_LIST,
        fields=JOB_FORMAT_FIELDS,
    )
