import pytest
from globus_sdk._testing import RegisteredResponse, load_response


@pytest.mark.parametrize("service_name", ["auth", "transfer", "groups", "search"])
def test_api_command_get(run_line, service_name):
    load_response(
        RegisteredResponse(
            service=service_name,
            path="/foo",
            json={"foo": "bar"},
        )
    )

    result = run_line(f"globus api {service_name}  get /foo")
    assert (
        result.output
        == """\
{
  "foo": "bar"
}
"""
    )
