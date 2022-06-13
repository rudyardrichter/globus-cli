from globus_cli.parsing import group

from .list import list_command
from .show import show_command


@group("timer")
def timer_command():
    """Schedule and manage jobs in Globus Timer"""


timer_command.add_command(list_command)
timer_command.add_command(show_command)
