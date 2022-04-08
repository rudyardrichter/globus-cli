import click
import pytest

from globus_cli.commands.api import HeaderParamType, QueryParamType, detect_content_type


@pytest.mark.parametrize(
    "content_type_arg,expect",
    [
        ("json", "application/json"),
        ("form", "application/x-www-form-urlencoded"),
        ("text", "text/plain"),
        ("auto", None),
    ],
)
def test_detect_content_type_no_body(content_type_arg, expect):
    assert detect_content_type(content_type_arg, None) == expect


def test_auto_detect_content_type_from_body():
    assert detect_content_type("auto", "{}") == "application/json"
    assert detect_content_type("auto", "x=y") == "application/x-www-form-urlencoded"
    assert detect_content_type("auto", "{") is None
    # things that would be form-data if not for...
    # has newline
    assert detect_content_type("auto", "x=y\nk=v") is None
    # no equal-sign
    assert detect_content_type("auto", "xy") is None


def test_query_param_parsing(runner):
    # simple case
    @click.command()
    @click.option("-q", type=QueryParamType())
    def foo(q):
        x, y = q
        click.echo(f"x={x} y={y}")

    result = runner.invoke(foo, ["-q", "k=v"])
    assert result.output == "x=k y=v\n"

    result = runner.invoke(foo, ["-q", "kv"])
    assert result.exit_code == 2
    assert "invalid query param" in result.output

    # multiple case
    @click.command()
    @click.option("-q", type=QueryParamType(), multiple=True)
    def foo(q):
        for param in q:
            x, y = param
            click.echo(f"x={x} y={y}")

    result = runner.invoke(foo, [])
    assert result.output == ""
    result = runner.invoke(foo, ["-q", "k1=v1", "-q", "k2=v2"])
    assert result.output == "x=k1 y=v1\nx=k2 y=v2\n"


def test_header_parsing(runner):
    # simple case
    @click.command()
    @click.option("-h", type=HeaderParamType())
    def foo(h):
        x, y = h
        click.echo(f"x={x} y={y}")

    result = runner.invoke(foo, ["-h", "k: v"])
    assert result.output == "x=k y=v\n"

    result = runner.invoke(foo, ["-h", "kv"])
    assert result.exit_code == 2
    assert "invalid header param" in result.output

    result = runner.invoke(foo, ["-h", "k:v"])  # missing space
    assert result.exit_code == 2
    assert "invalid header param" in result.output

    # multiple case
    @click.command()
    @click.option("-h", type=HeaderParamType(), multiple=True)
    def foo(h):
        for param in h:
            x, y = param
            click.echo(f"x={x} y={y}")

    result = runner.invoke(foo, [])
    assert result.output == ""
    result = runner.invoke(foo, ["-h", "k1: v1", "-h", "k2: v2"])
    assert result.output == "x=k1 y=v1\nx=k2 y=v2\n"
