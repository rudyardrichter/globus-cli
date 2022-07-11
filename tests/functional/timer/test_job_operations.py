import json
import uuid
from typing import cast
from unittest import mock

import pytest
import responses
from globus_sdk import TimerClient, TransferClient
from globus_sdk._testing import RegisteredResponse, load_response_set

from globus_cli.commands.timer._common import JOB_FORMAT_FIELDS

# NOTE: this is not quite the same as the "normal" job responses from
# create/update—definitely something to consider revisiting on the Timer API.
DELETE_RESPONSE = {
    "callback_body": {
        "body": {
            "DATA": [
                {
                    "DATA_TYPE": "transfer_item",
                    "checksum_algorithm": None,
                    "destination_path": "/~/file1.txt",
                    "external_checksum": None,
                    "recursive": False,
                    "source_path": "/share/godata/file1.txt",
                }
            ],
            "DATA_TYPE": "transfer",
            "delete_destination_extra": False,
            "destination_endpoint": "ddb59af0-6d04-11e5-ba46-22000b92c6ec",
            "encrypt_data": False,
            "fail_on_quota_errors": False,
            "notify_on_failed": True,
            "notify_on_inactive": True,
            "notify_on_succeeded": True,
            "preserve_timestamp": False,
            "recursive_symlinks": "ignore",
            "skip_source_errors": False,
            "source_endpoint": "ddb59aef-6d04-11e5-ba46-22000b92c6ec",
            "submission_id": "548ec2d3-b4fd-11ec-b87f-3912f602f346",
            "verify_checksum": False,
        }
    },
    "callback_url": "https://actions.automate.globus.org/transfer/transfer/run",
    "interval": None,
    "job_id": "e304f241-b77a-4e75-89f6-c431ddafe497",
    "n_tries": 1,
    "name": "example-timer-job",
    "owner": "5276fa05-eedf-46c5-919f-ad2d0160d1a9",
    "refresh_token": None,
    "results": [],
    "start": "2022-04-05T16:27:48",
    "status": "deleted",
    "stop_after": None,
    "stop_after_n": 1,
    "submitted_at": "2022-04-05T16:27:48.805427",
    "update_pending": True,
}


def test_show_job(run_line):
    meta = load_response_set(TimerClient.get_job).metadata
    assert meta
    result = run_line(["globus", "timer", "show", meta["job_id"]])
    assert result.exit_code == 0
    assert meta["job_id"] in result.output
    for field_name, _ in JOB_FORMAT_FIELDS:
        assert field_name in result.output


def test_list_jobs(run_line):
    meta = load_response_set(TimerClient.list_jobs).metadata
    assert meta
    result = run_line(["globus", "timer", "list"])
    assert result.exit_code == 0
    assert all(job_id in result.output for job_id in meta["job_ids"])
    for field_name, _ in JOB_FORMAT_FIELDS:
        assert field_name in result.output


@pytest.mark.parametrize(
    "extra_args",
    [
        ["--interval", "600"],
        ["--stop-after-runs", "1"],
    ],
)
def test_create_job(run_line, extra_args, monkeypatch):
    meta = load_response_set(TimerClient.create_job).metadata
    meta_endpoints = load_response_set(TransferClient.get_endpoint).metadata
    assert meta
    assert meta_endpoints
    eid = meta_endpoints["endpoint_id"]
    base_args = [
        "globus",
        "timer",
        "create",
        "transfer",
        "--name",
        "test-transfer-command",
        "--source-endpoint",
        eid,
        "--dest-endpoint",
        eid,
        "--item",
        "/file_a",
        "/file_b",
        "false",
    ]
    load_response_set("cli.get_submission_id")
    RegisteredResponse(
        path=f"/endpoint/{eid}/autoactivate",
        service="transfer",
        method="POST",
        json={"code": "Activated.BogusCode"},
    ).add()
    mock_login_flow = mock.MagicMock()
    monkeypatch.setattr(
        "globus_cli.login_manager.LoginManager.run_login_flow", mock_login_flow
    )
    result = run_line(base_args + extra_args)
    assert result.exit_code == 0
    assert mock_login_flow.called


def test_update_job(run_line):
    job_id = str(uuid.UUID(int=0))
    new_name = "updated-job-name"
    # we're just going to use the create job resonse here, since the update route
    # returns exactly the same thing
    response = cast(
        dict, load_response_set(TimerClient.create_job).lookup("default").json
    )
    response["name"] = new_name
    responses.add(
        "PATCH",
        f"https://timer.automate.globus.org/jobs/{job_id}",
        json=response,
    )
    result = run_line(
        ["globus", "timer", "update", job_id, "--name", new_name, "-F", "json"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == response


def test_delete_job(run_line):
    job_id = str(uuid.UUID(int=0))
    responses.add(
        "DELETE",
        f"https://timer.automate.globus.org/jobs/{job_id}",
        json=DELETE_RESPONSE,
    )
    result = run_line(["globus", "timer", "delete", job_id, "-F", "json"])
    assert result.exit_code == 0
    assert json.loads(result.output) == DELETE_RESPONSE
