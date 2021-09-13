import pytest


def test_username_not_in_idset(run_line, load_api_fixtures):
    """trying to 'session update' with an identity not in your identity set results in
    an error"""
    load_api_fixtures("foo_user_info.yaml")
    result = run_line("globus session update sirosen@globusid.org", assert_exit_code=1)
    assert "'sirosen@globusid.org' is not in your identity set" in result.stderr


@pytest.mark.parametrize(
    "userparam", ["sirosen@globusid.org", "f4ee724c-b27c-4ccc-8237-989aa4085af4"]
)
def test_mix_user_and_domains(run_line, load_api_fixtures, userparam):
    load_api_fixtures("foo_user_info.yaml")
    result = run_line(
        f"globus session update uchicago.edu {userparam}", assert_exit_code=2
    )
    assert (
        "domain-type identities and user-type identities are mutually exclusive"
        in result.stderr
    )


@pytest.mark.parametrize(
    "idparam",
    ["sirosen@globusid.org", "f4ee724c-b27c-4ccc-8237-989aa4085af4", "uchicago.edu"],
)
def test_all_mutex(run_line, load_api_fixtures, idparam):
    load_api_fixtures("foo_user_info.yaml")
    result = run_line(f"globus session update --all {idparam}", assert_exit_code=2)
    assert "IDENTITY values and --all are mutually exclusive" in result.stderr


def test_username_flow(
    run_line, load_api_fixtures, mock_remote_session, mock_link_flow
):
    mock_remote_session.return_value = True

    data = load_api_fixtures("foo_user_info.yaml")
    username = data["metadata"]["username"]
    user_id = data["metadata"]["user_id"]

    result = run_line(f"globus session update {username}")

    assert "You have successfully updated your CLI session." in result.output

    mock_link_flow.assert_called_once()
    _call_args, call_kwargs = mock_link_flow.call_args
    assert "session_params" in call_kwargs
    assert "session_required_identities" in call_kwargs["session_params"]
    assert call_kwargs["session_params"]["session_required_identities"] == user_id


def test_domain_flow(run_line, load_api_fixtures, mock_remote_session, mock_link_flow):
    mock_remote_session.return_value = True

    load_api_fixtures("foo_user_info.yaml")

    result = run_line("globus session update uchicago.edu")

    assert "You have successfully updated your CLI session." in result.output

    mock_link_flow.assert_called_once()
    _call_args, call_kwargs = mock_link_flow.call_args
    assert "session_params" in call_kwargs
    assert "session_required_single_domain" in call_kwargs["session_params"]
    assert (
        call_kwargs["session_params"]["session_required_single_domain"]
        == "uchicago.edu"
    )


def test_all_flow(
    run_line, load_api_fixtures, mock_remote_session, mock_local_server_flow
):
    mock_remote_session.return_value = False

    data = load_api_fixtures("foo_user_info.yaml")
    ids = [x["user_id"] for x in data["metadata"]["linked_ids"]]
    ids.append(data["metadata"]["user_id"])

    result = run_line("globus session update --all")

    assert "You have successfully updated your CLI session." in result.output

    mock_local_server_flow.assert_called_once()
    _call_args, call_kwargs = mock_local_server_flow.call_args
    assert "session_params" in call_kwargs
    assert "session_required_identities" in call_kwargs["session_params"]
    assert set(
        call_kwargs["session_params"]["session_required_identities"].split(",")
    ) == set(ids)
