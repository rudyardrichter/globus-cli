import json
from typing import List, Optional, Tuple

import click
import globus_sdk

from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command, group
from globus_cli.termio import formatted_print


class QueryParamType(click.ParamType):
    def get_metavar(self, param):
        return "x=y"

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if value is None:
            return None
        if "=" not in value:
            self.fail("invalid query param", param=param, ctx=ctx)
        left, right = value.split("=", 1)
        return (left, right)


def _deduce_content_type(content_type: str, body: Optional[str]) -> Optional[str]:
    if content_type == "json":
        return "application/json"
    elif content_type == "form":
        return "application/x-www-form-urlencoded"
    elif content_type == "auto":
        if body is None:
            return None
        try:
            json.loads(body)
            return "application/json"
        except ValueError:
            return None
    else:
        raise NotImplementedError(f"did not recognize content-type '{content_type}'")


_SERVICE_MAP = {
    "auth": LoginManager.AUTH_RS,
    "groups": LoginManager.GROUPS_RS,
    "search": LoginManager.SEARCH_RS,
    "transfer": LoginManager.TRANSFER_RS,
}


def _get_client(
    login_manager: LoginManager, service_name: str
) -> globus_sdk.BaseClient:
    if service_name == "auth":
        return login_manager.get_auth_client()
    elif service_name == "groups":
        return login_manager.get_groups_client()
    elif service_name == "search":
        return login_manager.get_search_client()
    elif service_name == "transfer":
        return login_manager.get_transfer_client()
    else:
        raise NotImplementedError(f"unrecognized service: {service_name}")


def _format_json(res):
    click.echo(json.dumps(res.data, indent=2, separators=(",", ": "), sort_keys=True))


@group("api")
def api_command():
    """Make API calls to Globus services"""


for service_name in _SERVICE_MAP:

    @command(service_name, help=f"Make API calls to Globus {service_name.title()}")
    @LoginManager.requires_login(_SERVICE_MAP[service_name])
    @click.argument(
        "method",
        type=click.Choice(
            ("HEAD", "GET", "PUT", "POST", "PATCH", "DELETE"), case_sensitive=False
        ),
    )
    @click.argument("path")
    @click.option("--query-param", "-Q", type=QueryParamType(), multiple=True)
    @click.option(
        "--content-type",
        type=click.Choice(("json", "form", "text", "none", "auto")),
        default="auto",
    )
    @click.option("--body")
    def service_command(
        *,
        login_manager: LoginManager,
        method: str,
        path: str,
        query_param: List[Tuple[str, str]],
        body: Optional[str],
        content_type: str,
    ):
        client = _get_client(login_manager, service_name)
        query_params_d = {}
        for param_name, param_value in query_param:
            query_params_d[param_name] = param_value
        headers = {}
        if content_type != "none":
            deduced_content_type = _deduce_content_type(content_type, body)
            if deduced_content_type is not None:
                headers["Content-Type"] = deduced_content_type
        res = client.request(
            method.upper(),
            path,
            query_params=query_params_d,
            data=body,
            headers=headers,
        )
        formatted_print(res, text_format=_format_json)

    api_command.add_command(service_command)
