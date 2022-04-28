import click

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import collection_id_arg, command
from globus_cli.principal_resolver import default_identity_id_resolver
from globus_cli.services.gcs import connector_id_to_display_name
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print
from globus_cli.types import FIELD_LIST_T
from globus_cli.utils import filter_fields, sorted_json_field

STANDARD_FIELDS: FIELD_LIST_T = [
    ("Display Name", "display_name"),
    ("Owner", default_identity_id_resolver.field),
    ("ID", "id"),
    ("Collection Type", "collection_type"),
    ("Storage Gateway ID", "storage_gateway_id"),
    ("Connector", lambda x: connector_id_to_display_name(x["connector_id"])),
    ("Allow Guest Collections", "allow_guest_collections"),
    ("Disable Anonymous Writes", "disable_anonymous_writes"),
    ("High Assurance", "high_assurance"),
    ("Authentication Timeout", "authentication_timeout_mins"),
    ("Multi-factor Authentication", "require_mfa"),
    ("Manager URL", "manager_url"),
    ("HTTPS URL", "https_url"),
    ("TLSFTP URL", "tlsftp_url"),
    ("Force Encryption", "force_encryption"),
    ("Public", "public"),
    ("Organization", "organization"),
    ("Department", "department"),
    ("Keywords", "keywords"),
    ("Description", "description"),
    ("Contact E-mail", "contact_email"),
    ("Contact Info", "contact_info"),
    ("Collection Info Link", "info_link"),
]

PRIVATE_FIELDS: FIELD_LIST_T = [
    ("Root Path", "root_path"),
    ("Default Directory", "default_directory"),
    ("Sharing Path Restrictions", sorted_json_field("sharing_restrict_paths")),
    ("Sharing Allowed Users", "sharing_users_allow"),
    ("Sharing Denied Users", "sharing_users_deny"),
    ("Sharing Allowed POSIX Groups", "policies.sharing_groups_allow"),
    ("Sharing Denied POSIX Groups", "policies.sharing_groups_deny"),
]


@command("show", short_help="Show a Collection definition")
@collection_id_arg
@click.option(
    "--include-private-policies",
    is_flag=True,
    help=(
        "Include private policies. Requires administrator role on the endpoint. "
        "Some policy data may only be visible in `--format JSON` output"
    ),
)
@LoginManager.requires_login(LoginManager.TRANSFER_RS, LoginManager.AUTH_RS)
def collection_show(
    *, login_manager: LoginManager, include_private_policies, collection_id
):
    """
    Display a Mapped or Guest Collection
    """
    gcs_client = login_manager.get_gcs_client(collection_id=collection_id)

    query_params = {}
    fields: FIELD_LIST_T = STANDARD_FIELDS

    if include_private_policies:
        query_params["include"] = "private_policies"
        fields += PRIVATE_FIELDS

    res = gcs_client.get_collection(collection_id, query_params=query_params)

    # walk the list of all known fields and reduce the rendering to only look
    # for fields which are actually present
    real_fields = filter_fields(fields, res)

    formatted_print(
        res,
        text_format=FORMAT_TEXT_RECORD,
        fields=real_fields,
    )
