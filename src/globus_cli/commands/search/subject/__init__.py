from globus_cli.parsing import group

from .delete import delete_command
from .show import show_command


@group("subject", short_help="Manage data by subject")
def subject_command() -> None:
    """View and manage individual documents in an index by subject"""


subject_command.add_command(delete_command)
subject_command.add_command(show_command)
