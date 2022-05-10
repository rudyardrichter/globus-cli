from globus_sdk import TimerClient
from globus_sdk._testing import load_response_set


def test_create_transfer(run_line):
    meta = load_response_set(TimerClient.create_job).metadata
    result = run_line(
        [
            "globus", "timer", "create", "transfer",
            "--name", "test-create-transfer",
            "--interval", "48h",
            "--source-endpoint", "",
            "--dest-endpoint", "",
            "--item", "/share/godata/file1.txt", "/~/file1.txt", "false",
        ]
    )
    import pdb; pdb.set_trace()
    pass
