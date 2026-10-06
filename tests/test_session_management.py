import json
from io import StringIO
from unittest.mock import patch

import pytest
import requests

from portal_client import parser
from portal_client.session_management import (
    SessionManagementApiClient,
    create_vm_cli,
    disable_debug_mode_cli,
    enable_debug_mode_cli,
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

    @pytest.mark.parametrize(
        "enabled, action", [(True, "EnableDebugMode"), (False, "DisableDebugMode")]
    )
    def test_set_debug_mode(self, requests_mock, enabled, action):
        expected_response = {"id": "vm-123", "debugModeEnabled": enabled}
        requests_mock.post(
            f"https://session-management.innoactive.io/VirtualMachines/vm-123/{action}",
            json=expected_response,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.set_debug_mode("vm-123", 456, enabled=enabled)

        assert result == expected_response
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "456"

    def test_set_debug_mode_error_response(self, requests_mock):
        requests_mock.post(
            "https://session-management.innoactive.io/VirtualMachines/vm-123/EnableDebugMode",
            text="Forbidden",
            status_code=403,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with pytest.raises(requests.HTTPError):
                client.set_debug_mode("vm-123", 456, enabled=True)

    def test_get_vm(self, requests_mock):
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines/vm-123",
            json={"id": "vm-123", "publicIp": "1.2.3.4"},
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.get_vm("vm-123", 456)

        assert result == {"id": "vm-123", "publicIp": "1.2.3.4"}
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "456"

    def test_create_vm(self, requests_mock):
        requests_mock.post(
            "https://session-management.innoactive.io/VirtualMachines",
            json={"id": "vm-123", "state": "Created"},
            status_code=201,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            result = client.create_vm(
                organization_id=456,
                region="eu-central-1",
                size="l4-small",
                expiration="01:00:00",
                image="dev/latest",
                debug_mode=True,
            )

        assert result == {"id": "vm-123", "state": "Created"}
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "456"
        assert requests_mock.last_request.json() == {
            "region": "eu-central-1",
            "size": "l4-small",
            "image": "dev/latest",
            "expirationTimeSpan": "01:00:00",
            "debugModeEnabled": True,
        }

    def test_destroy_vm(self, requests_mock):
        requests_mock.post(
            "https://session-management.innoactive.io/VirtualMachines/vm-123/Destroy",
            json={"id": "vm-123", "state": "Started"},
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            client.destroy_vm("vm-123", 456)

        assert requests_mock.last_request.method == "POST"
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "456"

    def test_list_vm_sizes(self, requests_mock):
        expected_response = {"vmSizes": [{"name": "l4-small", "isEnabled": True}]}
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines/Sizes",
            json=expected_response,
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            assert client.list_vm_sizes() == expected_response

    def test_list_vm_images_passes_only_given_filters(self, requests_mock):
        requests_mock.get(
            "https://session-management.innoactive.io/VirtualMachines/Images",
            json=[],
        )

        client = SessionManagementApiClient()
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            client.list_vm_images(instance="dev", gpu_type="l4")

        assert requests_mock.last_request.qs == {"instance": ["dev"], "gputype": ["l4"]}

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

    @pytest.mark.parametrize(
        "cli, action, enabled",
        [
            (enable_debug_mode_cli, "EnableDebugMode", True),
            (disable_debug_mode_cli, "DisableDebugMode", False),
        ],
    )
    def test_debug_mode_cli(self, requests_mock, cli, action, enabled):
        expected_response = {"id": "vm-123", "debugModeEnabled": enabled}
        requests_mock.post(
            f"https://session-management.innoactive.io/VirtualMachines/vm-123/{action}",
            json=expected_response,
        )

        class MockArgs:
            vm_id = "vm-123"
            org_id = 456

        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                cli(MockArgs())

        assert json.loads(mock_stdout.getvalue().strip()) == expected_response

    def test_create_vm_cli(self, requests_mock):
        requests_mock.post(
            "https://session-management.innoactive.io/VirtualMachines",
            json={"id": "vm-123"},
            status_code=201,
        )

        class MockArgs:
            org_id = 456
            region = "eu-central-1"
            size = "l4-small"
            expiration = "01:00:00"
            image = None
            debug_mode = False

        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
                create_vm_cli(MockArgs())

        assert json.loads(mock_stdout.getvalue().strip()) == {"id": "vm-123"}
        assert requests_mock.last_request.json()["image"] is None


SESSIONS_URL = "https://session-management.innoactive.io/v2/Sessions"
DEVICES_URL = "https://session-management.innoactive.io/Devices"
SESSION_ID = "5d0c1a3e-6f5b-4c1e-9a3b-2f9d8e7c6b5a"
DEVICE_ID = "0b6e2f4a-1c3d-4e5f-8a9b-7c6d5e4f3a2b"


class TestSessions:
    @pytest.fixture(autouse=True)
    def bearer_token(self):
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            yield

    def test_list_sessions_includes_running_and_failed_ones(self, requests_mock):
        expected_response = {"items": [{"id": SESSION_ID}], "totalResults": 1}
        requests_mock.get(SESSIONS_URL, json=expected_response)

        result = SessionManagementApiClient().list_sessions(
            organization_id=123,
            user_id="7",
            app_id="42",
            render_type="RemoteRendered",
            created_after="2026-10-01T00:00:00Z",
            page=2,
            page_size=5,
        )

        assert result == expected_response
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "123"
        # Session management leaves out running and failed sessions without includeFailed
        assert requests_mock.last_request.qs == {
            "useridentifier": ["7"],
            "appid": ["42"],
            "rendertype": ["remoterendered"],
            "from": ["2026-10-01t00:00:00z"],
            "includefailed": ["true"],
            "page": ["2"],
            "pagesize": ["5"],
        }

    def test_list_sessions_completed_only(self, requests_mock):
        requests_mock.get(SESSIONS_URL, json={"items": []})

        SessionManagementApiClient().list_sessions(completed_only=True)

        assert requests_mock.last_request.qs == {}
        assert "Portal-Organization-Id" not in requests_mock.last_request.headers

    def test_get_session(self, requests_mock):
        requests_mock.get(
            f"{SESSIONS_URL}/{SESSION_ID}", json={"id": SESSION_ID, "state": "Running"}
        )

        result = SessionManagementApiClient().get_session(SESSION_ID, 123)

        assert result == {"id": SESSION_ID, "state": "Running"}
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "123"

    def test_request_session_from_given_device(self, requests_mock):
        requests_mock.post(SESSIONS_URL, json={"id": SESSION_ID})

        result = SessionManagementApiClient().request_session(
            organization_id=123,
            app_build_id=42,
            device_identifier="browser-1",
            device_id=DEVICE_ID,
            region="eu-central-1",
            vm_id="vm-1",
            extra_launch_arguments="--my-arg",
            language="de",
            xr_encryption=False,
            require_xr_gateway=True,
        )

        assert result == {"id": SESSION_ID}
        request = requests_mock.last_request
        assert request.headers["Portal-Organization-Id"] == "123"
        assert request.headers["Portal-Device-Id"] == DEVICE_ID
        assert request.json() == {
            "appBuildId": "42",
            "deviceIdentifier": "browser-1",
            "renderRegion": "eu-central-1",
            "virtualMachineId": "vm-1",
            "extraLaunchArguments": "--my-arg",
            "languageIsoCode": "de",
            "xrEncryption": False,
            "requireXRGateway": True,
        }

    def test_request_session_defaults_to_the_device_it_is_for(self, requests_mock):
        requests_mock.get(DEVICES_URL, json={"items": [{"id": DEVICE_ID}]})
        requests_mock.post(SESSIONS_URL, json={"id": SESSION_ID})

        SessionManagementApiClient().request_session(
            organization_id=123, app_build_id="42", device_identifier="browser-1"
        )

        device_lookup, session_request = requests_mock.request_history
        assert device_lookup.qs == {"identifier": ["browser-1"]}
        assert session_request.headers["Portal-Device-Id"] == DEVICE_ID
        assert session_request.json()["xrEncryption"] is None

    def test_request_session_without_access_to_the_device(self, requests_mock):
        requests_mock.get(DEVICES_URL, text="Forbidden", status_code=403)
        requests_mock.post(SESSIONS_URL, json={"id": SESSION_ID})

        with pytest.raises(requests.HTTPError):
            SessionManagementApiClient().request_session(
                organization_id=123, app_build_id="42", device_identifier="browser-1"
            )

        assert requests_mock.call_count == 1

    def test_terminate_session_from_given_device(self, requests_mock):
        requests_mock.post(
            f"{SESSIONS_URL}/{SESSION_ID}/Terminate",
            json={"id": SESSION_ID, "state": "Terminated"},
        )

        result = SessionManagementApiClient().terminate_session(
            SESSION_ID, organization_id=123, device_id=DEVICE_ID
        )

        assert result == {"id": SESSION_ID, "state": "Terminated"}
        assert requests_mock.call_count == 1
        assert requests_mock.last_request.headers["Portal-Device-Id"] == DEVICE_ID
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "123"

    def test_terminate_session_defaults_to_the_device_it_is_for(self, requests_mock):
        requests_mock.get(
            f"{SESSIONS_URL}/{SESSION_ID}",
            json={"id": SESSION_ID, "deviceIdentifier": "browser-1"},
        )
        requests_mock.get(DEVICES_URL, json={"items": [{"id": DEVICE_ID}]})
        requests_mock.post(
            f"{SESSIONS_URL}/{SESSION_ID}/Terminate",
            json={"id": SESSION_ID, "state": "Terminated"},
        )

        SessionManagementApiClient().terminate_session(SESSION_ID)

        _, device_lookup, termination = requests_mock.request_history
        assert device_lookup.qs == {"identifier": ["browser-1"]}
        assert termination.headers["Portal-Device-Id"] == DEVICE_ID


class TestSessionsCLI:
    @pytest.fixture(autouse=True)
    def bearer_token(self):
        with patch(
            "portal_client.session_management.get_bearer_authorization_header",
            return_value="Bearer test-token",
        ):
            yield

    def run(self, *argv):
        args = parser.parse_args(["sessions", *argv])
        with patch("sys.stdout", new_callable=StringIO) as mock_stdout:
            args.func(args)
        return json.loads(mock_stdout.getvalue())

    def test_list(self, requests_mock):
        requests_mock.get(SESSIONS_URL, json={"items": []})

        assert self.run("list", "--org-id", "1", "--user-id", "7") == {"items": []}
        assert requests_mock.last_request.headers["Portal-Organization-Id"] == "1"
        assert requests_mock.last_request.qs == {
            "useridentifier": ["7"],
            "includefailed": ["true"],
            "page": ["1"],
            "pagesize": ["10"],
        }

    def test_get(self, requests_mock):
        requests_mock.get(f"{SESSIONS_URL}/{SESSION_ID}", json={"id": SESSION_ID})

        assert self.run("get", SESSION_ID) == {"id": SESSION_ID}

    def test_request(self, requests_mock):
        requests_mock.post(SESSIONS_URL, json={"id": SESSION_ID})

        output = self.run(
            "request",
            "--org-id",
            "1",
            "--app-build-id",
            "42",
            "--device-identifier",
            "browser-1",
            "--device-id",
            DEVICE_ID,
            "--extra-launch-args=--my-arg",
            "--no-xr-encryption",
        )

        assert output == {"id": SESSION_ID}
        request = requests_mock.last_request
        assert request.headers["Portal-Device-Id"] == DEVICE_ID
        assert request.json() == {
            "appBuildId": "42",
            "deviceIdentifier": "browser-1",
            "renderRegion": None,
            "virtualMachineId": None,
            "extraLaunchArguments": "--my-arg",
            "languageIsoCode": None,
            "xrEncryption": False,
            "requireXRGateway": False,
        }

    def test_terminate(self, requests_mock):
        requests_mock.post(
            f"{SESSIONS_URL}/{SESSION_ID}/Terminate",
            json={"id": SESSION_ID, "state": "Terminated"},
        )

        output = self.run("terminate", SESSION_ID, "--device-id", DEVICE_ID)

        assert output == {"id": SESSION_ID, "state": "Terminated"}
        assert requests_mock.last_request.headers["Portal-Device-Id"] == DEVICE_ID
