from unittest.mock import patch

import requests_mock

from portal_client.client_application_uploader import ClientApplicationApiClient


def test_version_lookup_is_authenticated(requests_mock: requests_mock.Mocker):
    """The duplicate check before an upload has to authenticate: the backend only serves the *current* version of a
    client application anonymously, so an unauthenticated lookup reports an already existing - but by now superseded -
    version as missing, and the upload then fails later on the uniqueness constraint instead of aborting cleanly.
    """
    # Given a backend that serves the details of an existing client application version
    api_client = ClientApplicationApiClient(base_url="https://portal.test")
    requests_mock.get(
        "https://portal.test/api/client-applications/desktop-client/versions/1.2.3/",
        json={"version": "1.2.3"},
    )

    # When looking up that version
    with patch(
        "portal_client.client_application_uploader.get_authorization_header",
        return_value="Bearer token",
    ):
        response = api_client.retrieve_client_application_version(
            "desktop-client", "1.2.3"
        )

    # Then expect the request to have carried the credentials
    assert response.status_code == 200
    assert requests_mock.last_request.headers["Authorization"] == "Bearer token"
