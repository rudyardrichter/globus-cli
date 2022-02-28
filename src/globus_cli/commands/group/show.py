from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print

from ._common import (
    format_session_enforcement,
    group_id_arg,
    parse_roles,
    parse_visibility,
)


@group_id_arg
@command("show")
@LoginManager.requires_login(LoginManager.GROUPS_RS)
def group_show(
    *,
    login_manager: LoginManager,
    group_id: str,
):
    """Show a group definition"""
    groups_client = login_manager.get_groups_client()

    query_params = {"include": "my_memberships"}
    group = groups_client.get_group(group_id, query_params=query_params)

    formatted_print(
        group,
        text_format=FORMAT_TEXT_RECORD,
        fields=[
            ("Name", "name"),
            ("Description", "description"),
            ("Type", "group_type"),
            ("Visibility", parse_visibility),
            ("Session Enforcement", format_session_enforcement),
            ("Roles", parse_roles),
        ],
    )