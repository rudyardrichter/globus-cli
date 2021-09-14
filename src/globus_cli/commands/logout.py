import click
import globus_sdk
from globus_sdk import AuthAPIError

from globus_cli.login_manager import (
    delete_templated_client,
    internal_native_client,
    token_storage_adapter,
)
from globus_cli.login_manager.auth_flows import _STORE_CONFIG_USERINFO
from globus_cli.parsing import command
from globus_cli.services.auth import get_auth_client


def warnecho(msg):
    click.echo(click.style(msg, fg="yellow"), err=True)


_LOGOUT_EPILOG = """\
You are now successfully logged out of the Globus CLI.
You may also want to logout of any browser session you have with Globus:

  https://auth.globus.org/v2/web/logout

Before attempting any further CLI commands, you will have to login again using

  globus login
"""


@command(
    "logout",
    short_help="Logout of the Globus CLI",
    disable_options=["format", "map_http_status"],
)
@click.confirmation_option(
    prompt="Are you sure you want to logout?",
    help='Automatically say "yes" to all prompts',
)
@click.option(
    "--ignore-errors",
    help="Ignore any errors encountered during logout",
    is_flag=True,
    default=False,
)
def logout_command(ignore_errors):
    """
    Logout of the Globus CLI

    This command both removes all tokens used for authenticating the user from local
    storage and revokes them so that they cannot be used anymore globally.

    If an expected token cannot be found in local storage a warning will be raised
    as it is possible the token still exists and needs to be manually rescinded
    at https://auth.globus.org/consents for security.
    """
    # try to get the user's preferred username from userinfo
    # if an API error is raised, they probably are not logged in
    try:
        username = get_auth_client().oauth2_userinfo()["preferred_username"]
    except AuthAPIError:
        warnecho(
            "Unable to lookup username. You may not be logged in. "
            "Attempting logout anyway...\n"
        )
        username = None
    click.echo(
        "Logging out of Globus{}\n".format(" as " + username if username else "")
    )

    # first, try to delete the templated credentialed client
    # ignore failure (maybe creds are already invalidated or the client was deleted)
    try:
        delete_templated_client()
    except AuthAPIError:
        if not ignore_errors:
            warnecho(
                "Failure while deleting internal client. "
                "Please try logging out again",
            )
            click.get_current_context().exit(1)
        else:
            warnecho(
                "Warning: Failed to delete internal client. "
                "Continuing... (--ignore-errors)",
            )

    # because the client was deleted above, the tokens should all be revoked
    # but it could have been the `--ignore-errors` case, so take a shot at revoking
    # tokens
    # use the native client for this purpose so that we definitely have a valid API
    # client in this case
    native_client = internal_native_client()

    adapter = token_storage_adapter()

    for rs, tokendata in adapter.get_by_resource_server().items():
        for tok_key in ("access_token", "refresh_token"):
            token = tokendata[tok_key]

            try:
                native_client.oauth2_revoke_token(token)
            # if we network error, revocation failed -- print message and abort so
            # that the user can try again when the network is working
            except globus_sdk.NetworkError:
                if not ignore_errors:
                    warnecho(
                        "Failed to reach Globus to revoke tokens. "
                        "Because we cannot revoke these tokens, cancelling logout",
                    )
                    click.get_current_context().exit(1)
                else:
                    warnecho(
                        "Warning: Failed to reach Globus to revoke tokens. "
                        "Continuing... (--ignore-errors)",
                    )

        adapter.remove_tokens_for_resource_server(rs)

    adapter.remove_config(_STORE_CONFIG_USERINFO)

    click.echo(_LOGOUT_EPILOG)
