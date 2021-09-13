from unittest import mock

import pytest


@pytest.fixture
def mock_link_flow():
    with mock.patch("globus_cli.login_manager.manager.do_link_auth_flow") as m:
        yield m


@pytest.fixture
def mock_local_server_flow():
    with mock.patch("globus_cli.login_manager.manager.do_local_server_auth_flow") as m:
        yield m


@pytest.fixture
def mock_remote_session():
    with mock.patch("globus_cli.login_manager.manager.is_remote_session") as m:
        yield m
