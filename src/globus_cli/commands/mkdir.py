import click

from globus_cli.login_manager import requires_login
from globus_cli.parsing import ENDPOINT_PLUS_REQPATH, command
from globus_cli.services.transfer import (
    TRANSFER_RESOURCE_SERVER,
    autoactivate,
    get_client,
)
from globus_cli.termio import FORMAT_TEXT_RAW, formatted_print


@command(
    "mkdir",
    short_help="Create a directory on an endpoint",
    adoc_examples="""Create a directory under your home directory:

[source,bash]
----
$ ep_id=ddb59aef-6d04-11e5-ba46-22000b92c6ec
$ mkdir ep_id:~/testfolder
----
""",
)
@click.argument("endpoint_plus_path", type=ENDPOINT_PLUS_REQPATH)
@requires_login(TRANSFER_RESOURCE_SERVER)
def mkdir_command(endpoint_plus_path):
    """Make a directory on an endpoint at the given path.

    {AUTOMATIC_ACTIVATION}
    """
    endpoint_id, path = endpoint_plus_path

    client = get_client()
    autoactivate(client, endpoint_id, if_expires_in=60)

    res = client.operation_mkdir(endpoint_id, path=path)
    formatted_print(res, text_format=FORMAT_TEXT_RAW, response_key="message")
