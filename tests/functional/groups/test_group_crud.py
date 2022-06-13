"""CRUD = Create Read Update Delete"""
import json

import pytest
import responses
from globus_sdk._testing import load_response_set, register_response_set


@pytest.fixture(autouse=True, scope="session")
def _register_group_responses():
    group_id = "efdab3ca-cff1-11e4-9b86-123139260d4e"

    register_response_set(
        "get_group?include=memberships",
        dict(
            default=dict(
                service="groups",
                path=f"/groups/{group_id}",
                json={
                    "description": "Ipso facto",
                    "enforce_session": False,
                    "group_type": "regular",
                    "id": group_id,
                    "memberships": [
                        {
                            "group_id": group_id,
                            "identity_id": "ae332d86-d274-11e5-b885-b31714a110e9",
                            "membership_fields": {
                                "department": "Globus Testing",
                                "email": "sirosen@globus.org",
                                "field_of_science": "CS",
                                "institution": "Computation Institute",
                                "phone": "867-5309",
                            },
                            "role": "admin",
                            "status": "active",
                            "username": "sirosen@globusid.org",
                        },
                        {
                            "group_id": group_id,
                            "identity_id": "508e5ef6-cb9b-11e5-abe1-431ce3f42be1",
                            "membership_fields": {},
                            "role": "member",
                            "status": "invited",
                            "username": "sirosen@xsede.org",
                        },
                        {
                            "group_id": group_id,
                            "identity_id": "ae2f7f60-d274-11e5-b879-afc598dd59d4",
                            "membership_fields": {
                                "institution": "University of Chicago",
                                "name": "Bryce Allen",
                                "department": "Globus",
                            },
                            "role": "member",
                            "status": "active",
                            "username": "ballen@globusid.org",
                        },
                        {
                            "group_id": group_id,
                            "identity_id": "b0e8f24a-d274-11e5-8c98-8fd1e61c0a76",
                            "membership_fields": {
                                "current_project_name": "Petrel support",
                                "department": "UChicago",
                            },
                            "role": "member",
                            "status": "rejected",
                            "username": "smartin@globusid.org",
                        },
                        {
                            "group_id": group_id,
                            "identity_id": "6b487878-d2a1-11e5-b689-a7dd99513a65",
                            "membership_fields": {
                                "department": (
                                    "Columbia University department "
                                    "of Witchcraft and History"
                                ),
                            },
                            "role": "member",
                            "status": "active",
                            "username": "jss2253@columbia.edu",
                        },
                        {
                            "group_id": group_id,
                            "identity_id": "ae2a1750-d274-11e5-b867-e74762c29f57",
                            "membership_fields": {},
                            "role": "member",
                            "status": "invited",
                            "username": "bjmc@globusid.org",
                        },
                    ],
                    "name": "Claptrap Presents Claptrap's Rough Riders",
                    "parent_id": None,
                    "policies": {
                        "authentication_assurance_timeout": 28800,
                        "group_members_visibility": "managers",
                        "group_visibility": "private",
                        "is_high_assurance": False,
                        "join_requests": False,
                        "signup_fields": [],
                    },
                    "session_limit": 28800,
                    "session_timeouts": {
                        "ae341a98-d274-11e5-b888-dbae3a8ba545": {
                            "expire_time": "2022-02-08T06:05:54+00:00",
                            "expires_in": 0,
                        }
                    },
                },
                metadata={
                    "group_id": group_id,
                    "known_members": [
                        {
                            "role": "admin",
                            "status": "active",
                            "username": "sirosen@globusid.org",
                        },
                        {
                            "role": "member",
                            "status": "invited",
                            "username": "bjmc@globusid.org",
                        },
                        {
                            "role": "member",
                            "status": "rejected",
                            "username": "smartin@globusid.org",
                        },
                    ],
                },
            )
        ),
    )


def test_group_list(run_line):
    """
    Runs globus group list and validates results
    """
    meta = load_response_set("cli.groups").metadata

    group1_id = meta["group1_id"]
    group2_id = meta["group2_id"]
    group1_name = meta["group1_name"]
    group2_name = meta["group2_name"]

    result = run_line("globus group list")

    assert group1_id in result.output
    assert group2_id in result.output
    assert group1_name in result.output
    assert group2_name in result.output


def test_group_show(run_line):
    """
    Basic success test for globus group show
    """
    meta = load_response_set("cli.groups").metadata

    group1_id = meta["group1_id"]
    group1_name = meta["group1_name"]
    group1_description = meta["group1_description"]

    result = run_line(f"globus group show {group1_id}")

    assert group1_name in result.output
    assert group1_description in result.output


def test_group_create(run_line):
    """
    Basic success test for globus group create
    """
    meta = load_response_set("cli.groups").metadata

    group1_id = meta["group1_id"]
    group1_name = meta["group1_name"]
    group1_description = meta["group1_description"]

    result = run_line(
        f"globus group create '{group1_name}' --description '{group1_description}'"
    )

    assert f"Group {group1_id} created successfully" in result.output


def test_group_update(run_line):
    """
    Basic success test for globus group update
    Confirms existing values are included in the put document when
    not specified by options
    """
    meta = load_response_set("cli.groups").metadata

    group1_id = meta["group1_id"]
    group1_name = meta["group1_name"]
    group1_description = meta["group1_description"]
    new_name = "New Name"
    new_description = "New Description"

    # update name
    result = run_line(f"globus group update {group1_id} --name '{new_name}'")
    assert "Group updated successfully" in result.output

    # confirm description is in the put document with the pre-existing value
    last_req = responses.calls[-1].request
    sent = json.loads(last_req.body)
    assert sent["name"] == new_name
    assert sent["description"] == group1_description

    # update description
    result = run_line(
        f"globus group update {group1_id} --description '{new_description}'"
    )
    assert "Group updated successfully" in result.output

    # confirm name is in the put document with the pre-existing value
    last_req = responses.calls[-1].request
    sent = json.loads(last_req.body)
    assert sent["name"] == group1_name
    assert sent["description"] == new_description

    # update both name and description
    result = run_line(
        f"globus group update {group1_id} "
        f"--name '{new_name}' --description '{new_description}'"
    )
    assert "Group updated successfully" in result.output

    # confirm both fields use new value
    last_req = responses.calls[-1].request
    sent = json.loads(last_req.body)
    assert sent["name"] == new_name
    assert sent["description"] == new_description


def test_group_delete(run_line):
    """
    Basic success test for globus group delete
    """
    meta = load_response_set("cli.groups").metadata

    group1_id = meta["group1_id"]

    result = run_line(f"globus group delete {group1_id}")

    assert "Group deleted successfully" in result.output
