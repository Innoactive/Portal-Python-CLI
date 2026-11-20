import json
from unittest.mock import patch

import pytest
import requests_mock

from portal_client import parser

BUILDS_URL = "https://portal.test/api/v2/application-builds/"


def _upload_build(requests_mock: requests_mock.Mocker, *flags):
    """Runs `applications v2 upload-build` against a mocked Portal and returns the JSON body that created the build."""
    requests_mock.post(BUILDS_URL, json={"id": 1}, status_code=201)
    args = parser.parse_args(
        [
            "applications",
            "v2",
            "upload-build",
            "build.zip",
            "--application-id",
            "app-1",
            "--version",
            "1.0.0",
            "--xr-platform",
            "win-non-vr",
            *flags,
        ]
    )
    with (
        patch(
            "portal_client.applications_v2.get_portal_backend_endpoint",
            return_value="https://portal.test",
        ),
        patch(
            "portal_client.applications_v2.get_authorization_header",
            return_value="Bearer ipat_test",
        ),
        patch("portal_client.applications_v2.ChunkedUploader") as uploader,
        patch("builtins.print"),
    ):
        uploader.return_value.upload_chunked_file.return_value = (
            f"{BUILDS_URL}chunked_uploads/1/"
        )
        args.func(args)
    return json.loads(requests_mock.last_request.text)


@pytest.mark.parametrize(
    "flags, expected",
    [
        (["--set-as-current-version"], True),
        (["--no-set-as-current-version"], False),
    ],
)
def test_upload_build_says_whether_the_build_goes_into_use(
    requests_mock, flags, expected
):
    assert _upload_build(requests_mock, *flags)["set_as_current_version"] is expected


def test_upload_build_leaves_it_to_portal_without_either_flag(requests_mock):
    # Portal's default differs: builds uploaded by people go into use, those uploaded with an access token don't
    assert "set_as_current_version" not in _upload_build(requests_mock)
