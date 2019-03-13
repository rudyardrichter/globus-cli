import base64
import uuid

import click
from globus_sdk import GlobusResponse

from globus_cli.parsing import common_options
from globus_cli.safeio import FORMAT_TEXT_TABLE, formatted_print, is_verbose, safeprint
from globus_cli.services.auth import get_auth_client


def _try_b32_decode(v):
    """
    Attempt to decode a b32-encoded username which is sometimes generated by
    internal Globus components.

    The expectation is that the string is a valid ID, username, or b32-encoded
    name. Therefore, we can do some simple checking on it.

    If it does not appear to be formatted correctly, return None.
    """
    # should start with "u_"
    if not v.startswith("u_"):
        return None
    # usernames have @ , we want to allow `u_foo@example.com`
    # b32 names never have @
    if "@" in v:
        return None
    # trim "u_"
    v = v[2:]
    # wrong length
    if len(v) != 26:
        return None

    # append padding and uppercase so that b32decode will work
    v = v.upper() + (6 * "=")

    # try to decode
    try:
        return str(uuid.UUID(bytes=base64.b32decode(v)))
    # if it fails, I guess it's a username? Not much left to do
    except ValueError:
        return None


@click.command(
    "get-identities",
    short_help="Lookup Globus Auth Identities",
    help="Lookup Globus Auth Identities given one or more uuids "
    "and/or usernames. Either resolves each uuid to a username and "
    "vice versa, or use --verbose for tabular output.",
)
@common_options
@click.argument("values", required=True, nargs=-1)
def get_identities_command(values):
    """
    Executor for `globus get-identities`
    """
    client = get_auth_client()

    resolved_values = [_try_b32_decode(v) or v for v in values]

    # since API doesn't accept mixed ids and usernames,
    # split input values into separate lists
    ids = []
    usernames = []
    for val in resolved_values:
        try:
            uuid.UUID(val)
            ids.append(val)
        except ValueError:
            usernames.append(val)

    # make two calls to get_identities with ids and usernames
    # then combine the calls into one response
    results = []
    if len(ids):
        results += client.get_identities(ids=ids)["identities"]
    if len(usernames):
        results += client.get_identities(usernames=usernames)["identities"]
    res = GlobusResponse({"identities": results})

    def _custom_text_format(identities):
        """
        Non-verbose text output is customized
        """

        def resolve_identity(value):
            """
            helper to deal with variable inputs and uncertain response order
            """
            for identity in identities:
                if identity["id"] == value:
                    return identity["username"]
                if identity["username"] == value:
                    return identity["id"]
            return "NO_SUCH_IDENTITY"

        # standard output is one resolved identity per line in the same order
        # as the inputs. A resolved identity is either a username if given a
        # UUID vice versa, or "NO_SUCH_IDENTITY" if the identity could not be
        # found
        for val in resolved_values:
            safeprint(resolve_identity(val))

    formatted_print(
        res,
        response_key="identities",
        fields=[
            ("ID", "id"),
            ("Username", "username"),
            ("Full Name", "name"),
            ("Organization", "organization"),
            ("Email Address", "email"),
        ],
        # verbose output is a table. Order not guaranteed, may contain
        # duplicates
        text_format=(FORMAT_TEXT_TABLE if is_verbose() else _custom_text_format),
    )
