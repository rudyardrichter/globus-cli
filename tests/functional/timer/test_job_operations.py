from globus_sdk import TimerClient
from globus_sdk._testing import load_response_set

from globus_cli.commands.timer._common import JOB_FORMAT_FIELDS


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
