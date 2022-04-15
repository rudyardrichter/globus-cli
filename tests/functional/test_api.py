import pytest
from globus_sdk._testing import RegisteredResponse, load_response


@pytest.mark.parametrize("service_name", ["auth", "transfer", "groups", "search"])
@pytest.mark.parametrize("is_error_response", (False, True))
def test_api_command_get(run_line, service_name, is_error_response):
    load_response(
        RegisteredResponse(
            service=service_name,
            status=500 if is_error_response else 200,
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
