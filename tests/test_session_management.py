import json
from io import StringIO
from unittest.mock import patch

import pytest
import requests

from portal_client.session_management import (
    SessionManagementApiClient,
    extend_vm_expiration_cli,
    list_vms_cli,
    refresh_regions_cli,
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
        # Session management only reads the organization from this header
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "123"
        assert requests_mock.last_request.qs == {}
        assert (
            requests_mock.last_request.headers["Authorization"] == "Bearer test-token"
        )

    def test_list_vms_without_organization_sends_no_header(self, requests_mock):
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines",
            json={"items": []},
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            client.list_vms()

        assert "Portal-Organization-Id" not in requests_mock.last_request.headers

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
        request_body = requests_mock.last_request.json()
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "456"
        assert requests_mock.last_request.qs == {}
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

    def test_refresh_regions_success(self, requests_mock):
        # The endpoint returns 200 OK with no content body
        requests_mock.post(
            "https://session-management.innoactive.io/Regions/refresh",
            status_code=200,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.refresh_regions()

        assert result is None
        assert requests_mock.last_request.method == "POST"
        assert (
            requests_mock.last_request.headers["Authorization"] == "Bearer test-token"
        )

    def test_refresh_regions_error_response(self, requests_mock):
        requests_mock.post(
            "https://session-management.innoactive.io/Regions/refresh",
            text="Forbidden",
            status_code=403,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with pytest.raises(requests.HTTPError):
                client.refresh_regions()

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

    def test_refresh_regions_cli(self, requests_mock):
        # The endpoint returns 200 OK with no content body
        requests_mock.post(
            "https://session-management.innoactive.io/Regions/refresh",
            status_code=200,
        )

        class MockArgs:
            pass

        args = MockArgs()

        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                refresh_regions_cli(args)

        output = mock_stdout.getvalue().strip()
        assert "Successfully triggered a refresh" in output
        assert requests_mock.last_request.method == "POST"
