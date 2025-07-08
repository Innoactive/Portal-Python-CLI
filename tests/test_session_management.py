import json
from io import StringIO
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from portal_client.session_management import (
    SessionManagementApiClient,
    extend_vm_expiration_cli,
    list_vms_cli,
)


class TestSessionManagementApiClient:
    def test_list_vms_success(self, requests_mock):
        # Mock the API response
        expected_response = {
            "vms": [
                {"id": "vm-123", "name": "Test VM 1", "status": "running"},
                {"id": "vm-456", "name": "Test VM 2", "status": "stopped"},
            ]
        }
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines",
            json=expected_response,
        )

        # Test the client
        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.list_vms(organization_id=123)

        assert result == expected_response
        # Check the request URL contains the correct parameters
        request_url = requests_mock.last_request.url
        parsed_url = urlparse(request_url)
        query_params = parse_qs(parsed_url.query)
        assert query_params["organization_id"][0] == "123"
        assert (
            requests_mock.last_request.headers["Authorization"] == "Bearer test-token"
        )

    def test_extend_vm_expiration_success(self, requests_mock):
        # Mock the API response
        expected_response = {"message": "VM expiration extended successfully"}
        requests_mock.put(
            "https://session-management.innoactive.io/VirtualMachines/vm-123/Expiration",
            json=expected_response,
        )

        # Test the client
        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.extend_vm_expiration(
                vm_id="vm-123", organization_id=456, timespan="01:00:00"
            )

        assert result == expected_response
        # Check the request URL contains the correct parameters
        request_url = requests_mock.last_request.url
        parsed_url = urlparse(request_url)
        query_params = parse_qs(parsed_url.query)
        request_body = requests_mock.last_request.json()
        assert query_params["organization_id"][0] == "456"
        assert request_body["time"] == "01:00:00"
        assert (
            requests_mock.last_request.headers["Authorization"] == "Bearer test-token"
        )

    def test_list_vms_with_custom_base_url(self, requests_mock):
        # Test with custom base URL
        custom_url = "https://custom-session-mgmt.example.com"
        expected_response = {"vms": []}
        requests_mock.get(f"{custom_url}/VirtualMachines", json=expected_response)

        client = SessionManagementApiClient(base_url=custom_url)
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.list_vms(organization_id=123)

        assert result == expected_response

    def test_list_vms_error_response(self, requests_mock):
        # Mock an error response
        error_response = {"error": "Unauthorized"}
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines",
            json=error_response,
            status_code=401,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with pytest.raises(requests.HTTPError):
                client.list_vms(organization_id=123)


class TestSessionManagementCLI:
    def test_list_vms_cli(self, requests_mock):
        # Mock the API response
        expected_response = {"vms": [{"id": "vm-123", "name": "Test VM"}]}
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines",
            json=expected_response,
        )

        # Create mock args
        class MockArgs:
            org_id = 123

        args = MockArgs()

        # Capture stdout
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                list_vms_cli(args)

        # Verify output
        output = mock_stdout.getvalue().strip()
        assert json.loads(output) == expected_response

    def test_extend_vm_expiration_cli(self, requests_mock):
        # Mock the API response
        expected_response = {"message": "VM expiration extended successfully"}
        requests_mock.put(
            "https://session-management.innoactive.io/VirtualMachines/vm-123/Expiration",
            json=expected_response,
        )

        # Create mock args
        class MockArgs:
            vm_id = "vm-123"
            org_id = 456
            time = 60

        args = MockArgs()

        # Capture stdout
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                extend_vm_expiration_cli(args)

        # Verify output
        output = mock_stdout.getvalue().strip()
        assert json.loads(output) == expected_response
