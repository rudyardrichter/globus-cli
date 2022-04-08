import json
from typing import List, Optional, TextIO, Tuple

import click
import globus_sdk

from globus_cli import termio, version
from globus_cli.login_manager import LoginManager
from globus_cli.parsing import command, group, mutex_option_group


class QueryParamType(click.ParamType):
    def get_metavar(self, param):
        return "Key=Value"

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if value is None:
            return None
        if "=" not in value:
            self.fail("invalid query param", param=param, ctx=ctx)
        left, right = value.split("=", 1)
        return (left, right)


class HeaderParamType(click.ParamType):
    def get_metavar(self, param):
        return '"Key: Value"'

    def convert(self, value, param, ctx):
        value = super().convert(value, param, ctx)
        if value is None:
            return None
        if ": " not in value:
            self.fail("invalid header param", param=param, ctx=ctx)
        left, right = value.split(": ", 1)
        return (left, right)


def _looks_like_form(body: str) -> bool:
    # very weak detection for form-encoded data
    # if it's a single line of non-whitespace data with at least one '=', that will do!
    body = body.strip()
    if "\n" in body:
        return False
    if "=" not in body:
        return False
    return True


def _looks_like_json(body: str) -> bool:
    try:
        json.loads(body)
        return True
    except ValueError:
        return False


def _detect_content_type(content_type: str, body: Optional[str]) -> Optional[str]:
    if content_type == "json":
        return "application/json"
    elif content_type == "form":
        return "application/x-www-form-urlencoded"
    elif content_type == "text":
        return "text/plain"
    elif content_type == "auto":
        if body is not None:
            if _looks_like_json(body):
                return "application/json"
            if _looks_like_form(body):
                return "application/x-www-form-urlencoded"
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


def _get_url(service_name: str) -> str:
    return {
        "auth": "https://auth.globus.org/",
        "groups": "https://groups.api.globus.org/v2/",
        "search": "https://search.api/globus.org/",
        "transfer": "https://transfer.api.globus.org/v0.10/",
    }[service_name]


def _format_json(res: globus_sdk.GlobusHTTPResponse) -> None:
    click.echo(json.dumps(res.data, indent=2, separators=(",", ": "), sort_keys=True))


@group("api")
def api_command() -> None:
    """Make API calls to Globus services"""


for service_name in _SERVICE_MAP:

    @command(
        service_name,
        help=f"""\
Make API calls to Globus {service_name.title()}

The arguments are an HTTP method name and a path within the service to which the request
should be made. The path will be joined with the known service URL.
For example, a call of

    globus api {service_name} GET /foo/bar

sends a 'GET' request to '{_get_url(service_name)}foo/bar'
""",
    )
    @LoginManager.requires_login(_SERVICE_MAP[service_name])
    @click.argument(
        "method",
        type=click.Choice(
            ("HEAD", "GET", "PUT", "POST", "PATCH", "DELETE"), case_sensitive=False
        ),
    )
    @click.argument("path")
    @click.option(
        "--query-param",
        "-Q",
        type=QueryParamType(),
        multiple=True,
        help="A query parameter, given as 'key=value'. Use this option multiple "
        "times to pass multiple query parameters.",
    )
    @click.option(
        "--content-type",
        type=click.Choice(("json", "form", "text", "none", "auto")),
        default="auto",
        help="Use a specific Content-Type header for the request. "
        "The default (auto) detects a content type from the data being included in "
        "the request body, while the other names refer to common data encodings. "
        "Any explicit Content-Type header set via '--header' will override this",
    )
    @click.option(
        "--header",
        "-H",
        type=HeaderParamType(),
        multiple=True,
        help="A header, specified as 'Key: Value'. Use this option multiple "
        "times to pass multiple headers.",
    )
    @click.option("--body", help="A request body to include, as text")
    @click.option(
        "--body-file",
        type=click.File("r"),
        help="A request body to include, as a file. Mutually exclusive with --body",
    )
    @mutex_option_group("--body", "--body-file")
    def service_command(
        *,
        login_manager: LoginManager,
        method: str,
        path: str,
        query_param: List[Tuple[str, str]],
        header: List[Tuple[str, str]],
        body: Optional[str],
        body_file: Optional[TextIO],
        content_type: str,
    ):
        client = _get_client(login_manager, service_name)
        client.app_name = version.app_name + " raw-api-command"

        query_params_d = {}
        for param_name, param_value in query_param:
            query_params_d[param_name] = param_value

        if body_file:
            body = body_file.read()

        headers_d = {}
        if content_type != "none":
            detected_content_type = _detect_content_type(content_type, body)
            if detected_content_type is not None:
                headers_d["Content-Type"] = detected_content_type
        for header_name, header_value in header:
            headers_d[header_name] = header_value

        res = client.request(
            method.upper(),
            path,
            query_params=query_params_d,
            data=body,
            headers=headers_d,
        )
        termio.formatted_print(res, text_format=_format_json)

    api_command.add_command(service_command)
