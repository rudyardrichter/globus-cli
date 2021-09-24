from functools import reduce

import click

from globus_cli.endpointish import Endpointish
from globus_cli.login_manager import LoginManager
from globus_cli.parsing import collection_id_arg, command
from globus_cli.principal_resolver import default_identity_id_resolver
from globus_cli.services.gcs import connector_id_to_display_name, get_gcs_client
from globus_cli.termio import FORMAT_TEXT_RECORD, formatted_print
from globus_cli.utils import sorted_json_field

STANDARD_FIELDS = [
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
    ("Google Cloud Storage Project", "policies.project"),
]

PRIVATE_FIELDS = [
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
@LoginManager.requires_login(
    LoginManager.TRANSFER_RS, LoginManager.AUTH_RS, pass_manager=True
)
def collection_show(login_manager, *, include_private_policies, collection_id):
    """
    Show a Collection on the current Endpoint
    """
    endpoint_id = Endpointish(collection_id).get_collection_endpoint_id()
    login_manager.assert_logins(endpoint_id, assume_gcs=True)
    client = get_gcs_client(endpoint_id)

    query_params = {}
    fields = STANDARD_FIELDS

    if include_private_policies:
        query_params["include"] = "private_policies"
        fields += PRIVATE_FIELDS

    res = client.get_collection(collection_id, query_params=query_params)

    def get_key(key):
        if callable(key) and hasattr(key, "_filter_key"):
            return [key._filter_key]
        if isinstance(key, str):
            return key.split(".")
        return None

    def has_field(fields):
        return reduce(lambda acc, k: acc.get(k, {}), fields, res)

    # walk the list of all known fields and reduce the rendering to only look
    # for fields which are actually present
    formatted_print(
        res,
        text_format=FORMAT_TEXT_RECORD,
        fields=[
            (name, key)
            for name, key in fields
            if get_key(key) is None or has_field(get_key(key))
        ],
    )
