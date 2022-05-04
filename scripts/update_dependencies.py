#!/usr/bin/env python
from __future__ import annotations

import json
import pathlib
import re
import urllib.request

REPO_ROOT = pathlib.Path(__file__).parent.parent


class Abort(RuntimeError):
    pass


def get_sdk_latest() -> str:
    with urllib.request.urlopen("https://pypi.python.org/pypi/globus-sdk/json") as conn:
        version_data = json.load(conn)
    return str(version_data["info"]["version"])


def bump_sdk_version_on_file(path: pathlib.Path, new_version: str) -> None:
    print(f"updating globus-sdk in {path.relative_to(REPO_ROOT)} ... ", end="")
    with open(path) as fp:
        content = fp.read()
    match = re.search(r"globus-sdk==(\d+\.\d+\.\d+)", content)
    if not match:
        print("fail (abort)")
        raise Abort(f"{path} did not contain sdk version pattern")

    old_version = match.group(1)
    old_str = f"globus-sdk=={old_version}"
    new_str = f"globus-sdk=={new_version}"
    content = content.replace(old_str, new_str)
    with open(path, "w") as fp:
        fp.write(content)
    print("ok")


def bump_sdk_version() -> None:
    new_version = get_sdk_latest()
    bump_sdk_version_on_file(REPO_ROOT / "setup.py", new_version)
    bump_sdk_version_on_file(REPO_ROOT / ".pre-commit-config.yaml", new_version)


def main() -> None:
    bump_sdk_version()


if __name__ == "__main__":
    main()
