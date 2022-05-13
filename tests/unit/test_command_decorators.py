import click

from globus_cli.parsing import command


def test_custom_command_missing_param_helptext(runner):
    @command()
    @click.option("--bar", help="BAR-STRING-HERE", required=True)
    def foo(bar):
        click.echo(bar or "none")

    # call with `--help` to confirm help behavior
    result = runner.invoke(foo, ["--help"])
    assert result.exit_code == 0
    assert "BAR-STRING-HERE" in result.output

    # no args should produce the same, but with an exit status of 2
    result = runner.invoke(foo, [])
    assert result.exit_code == 2
    assert "BAR-STRING-HERE" in result.output
    # should include missing arg message
    assert "Missing option '--bar'" in result.output


def test_custom_command_missing_param_helptext_suppressed_when_args_present(runner):
    @command()
    @click.option("--bar", help="BAR-STRING-HERE", required=True)
    @click.option("--baz", help="BAZ-STRING-HERE", required=True)
    def foo(bar, baz):
        click.echo(bar or "none")
        click.echo(baz or "none")

    # call with `--help` to confirm help behavior
    result = runner.invoke(foo, ["--help"])
    assert result.exit_code == 0
    assert "BAR-STRING-HERE" in result.output
    assert "BAZ-STRING-HERE" in result.output

    # no args should produce the same, but with an exit status of 2
    # and a missing arg message
    result = runner.invoke(foo, [])
    assert result.exit_code == 2
    assert "Missing option" in result.output
    assert "BAR-STRING-HERE" in result.output
    assert "BAZ-STRING-HERE" in result.output

    # partial args should produce the missing arg message
    # but not helptext
    result = runner.invoke(foo, ["--bar", "X"])
    assert result.exit_code == 2
    assert "Missing option '--baz'" in result.output
    assert "BAR-STRING-HERE" not in result.output
    assert "BAZ-STRING-HERE" not in result.output
