import sys
import uuid
from typing import Callable, Dict, List, Optional

import click
import globus_sdk

from globus_cli.parsing import ParsedIdentity
from globus_cli.services.auth import CustomAuthClient

if sys.version_info >= (3, 8):
    from typing import Literal
else:
    from typing_extensions import Literal


def get_invite_formatter(
    case: Literal["accept", "decline"]
) -> Callable[[globus_sdk.GlobusHTTPResponse], None]:
    action_word = "Accepted" if case == "accept" else "Declined"

    def formatter(data: globus_sdk.GlobusHTTPResponse) -> None:
        values = [f"{x['identity_id']} ({x['username']})" for x in data[case]]
        if len(values) == 1:
            click.echo(f"{action_word} invitation as {values[0]}")
        else:
            click.echo(f"{action_word} invitation as")
            for v in values:
                click.echo(f"  {v}")

    return formatter


def build_invite_actions(
    auth_client: CustomAuthClient,
    groups_client: globus_sdk.GroupsClient,
    action: Literal["accept", "decline"],
    group_id: uuid.UUID,
    identity: Optional[ParsedIdentity],
) -> Dict[str, List[Dict[str, str]]]:
    if identity:
        identity_id = auth_client.maybe_lookup_identity_id(identity.value)
        if not identity_id:
            raise click.UsageError(
                f"Couldn't determine identity from value: {identity}"
            )
        return {action: [{"identity_id": identity_id}]}
    else:
        group = groups_client.get_group(group_id, include="my_memberships")
        invitations = [x for x in group["my_memberships"] if x["status"] == "invited"]
        if not invitations:
            raise click.ClickException(f"You have no invitations for {group_id}")
        return {action: [{"identity_id": x["identity_id"]} for x in invitations]}
