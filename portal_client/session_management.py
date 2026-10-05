#!/usr/bin/env python
# Session management API client for Portal

import argparse
import json
import logging
from urllib.parse import urljoin

import backoff
import requests

from .defaults import get_portal_session_management_endpoint
from .utils import get_bearer_authorization_header

logging.getLogger("backoff").addHandler(logging.StreamHandler())


# Session management scopes requests to an organization by this header, not a query parameter.
ORGANIZATION_HEADER = "Portal-Organization-Id"


class SessionManagementApiClient:
    """
    Class dealing with the session management API for Virtual Machines
    """

    def __init__(self, base_url=None) -> None:
        if base_url is None:
            base_url = get_portal_session_management_endpoint()
        self.base_url = base_url

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def _send(self, method, path, organization_id=None, **kwargs):
        """
        Send an authenticated request, scoped to an organization if one is given.
        Prints the error body and raises on a failed response; returns the parsed
        JSON body, or None for an empty one.
        """
        headers = {"Authorization": get_bearer_authorization_header()}
        if organization_id is not None:
            headers[ORGANIZATION_HEADER] = str(organization_id)

        response = requests.request(
            method,
            urljoin(self.base_url, path),
            headers=headers,
            timeout=30,
            **kwargs,
        )

        if not response.ok:
            print(response.text)
        response.raise_for_status()

        return response.json() if response.content else None

    def list_vms(self, organization_id=None):
        """
        List VMs for an organization: the caller's own, or all of them for an
        organization admin. Without an organization, lists the VMs that belong to
        none, which needs the global list_virtual_machines permission.
        """
        return self._send("GET", "/VirtualMachines", organization_id)

    def get_vm(self, vm_id, organization_id=None):
        """
        Get a single VM, including its state and public IP
        """
        return self._send("GET", f"/VirtualMachines/{vm_id}", organization_id)

    def create_vm(
        self,
        organization_id,
        region,
        size,
        expiration,
        image=None,
        debug_mode=False,
    ):
        """
        Create a VM for the caller in an organization; it is started right away.
        The expiration (HH:MM:SS) is how long until the VM is destroyed again.
        Debug mode opens the debug ports and needs the can_debug permission.
        """
        return self._send(
            "POST",
            "/VirtualMachines",
            organization_id,
            json={
                "region": region,
                "size": size,
                "image": image,
                "expirationTimeSpan": expiration,
                "debugModeEnabled": debug_mode,
            },
        )

    def destroy_vm(self, vm_id, organization_id=None):
        """
        Destroy a VM
        """
        return self._send("POST", f"/VirtualMachines/{vm_id}/Destroy", organization_id)

    def list_vm_sizes(self):
        """
        List the VM sizes and the regions each is available in
        """
        return self._send("GET", "/VirtualMachines/Sizes")

    def list_vm_images(self, instance=None, version=None, variant=None, gpu_type=None):
        """
        List the VM images and the regions each is available in
        """
        return self._send(
            "GET",
            "/VirtualMachines/Images",
            params={
                "instance": instance,
                "version": version,
                "variant": variant,
                "gpuType": gpu_type,
            },
        )

    def extend_vm_expiration(self, vm_id, organization_id, timespan):
        """
        Extend the expiration time of a VM
        """
        return self._send(
            "PUT",
            f"/VirtualMachines/{vm_id}/Expiration",
            organization_id,
            json={"time": timespan},
        )

    def set_debug_mode(self, vm_id, organization_id, enabled):
        """
        Enable or disable debug mode on a VM. Debug mode opens the debug ports
        (RDP, WinRM, ...) in the VM's firewall; needs the can_debug permission.
        """
        action = "EnableDebugMode" if enabled else "DisableDebugMode"
        return self._send("POST", f"/VirtualMachines/{vm_id}/{action}", organization_id)

    def refresh_regions(self):
        """
        Force an immediate refresh of the cached cloud resources (subnets,
        gateways, and VM images) across all regions, bypassing the configured
        cache expiry. Use after publishing a new VM image so it is picked up
        without waiting for the background refresh cycle. Admin only.
        """
        self._send("POST", "/Regions/refresh")


def list_vms_cli(args):
    """CLI wrapper for listing VMs"""
    client = SessionManagementApiClient()
    vms_response = client.list_vms(organization_id=args.org_id)
    print(json.dumps(vms_response))


def get_vm_cli(args):
    """CLI wrapper for getting a single VM"""
    client = SessionManagementApiClient()
    print(json.dumps(client.get_vm(args.vm_id, args.org_id)))


def create_vm_cli(args):
    """CLI wrapper for creating a VM"""
    client = SessionManagementApiClient()
    response = client.create_vm(
        organization_id=args.org_id,
        region=args.region,
        size=args.size,
        expiration=args.expiration,
        image=args.image,
        debug_mode=args.debug_mode,
    )
    print(json.dumps(response))


def destroy_vm_cli(args):
    """CLI wrapper for destroying a VM"""
    client = SessionManagementApiClient()
    print(json.dumps(client.destroy_vm(args.vm_id, args.org_id)))


def list_vm_sizes_cli(args):
    """CLI wrapper for listing VM sizes"""
    client = SessionManagementApiClient()
    print(json.dumps(client.list_vm_sizes()))


def list_vm_images_cli(args):
    """CLI wrapper for listing VM images"""
    client = SessionManagementApiClient()
    response = client.list_vm_images(
        instance=args.instance,
        version=args.version,
        variant=args.variant,
        gpu_type=args.gpu_type,
    )
    print(json.dumps(response))


def extend_vm_expiration_cli(args):
    """CLI wrapper for extending VM expiration"""
    client = SessionManagementApiClient()
    response = client.extend_vm_expiration(
        vm_id=args.vm_id, organization_id=args.org_id, timespan=args.time
    )
    print(json.dumps(response))


def enable_debug_mode_cli(args):
    """CLI wrapper for enabling debug mode on a VM"""
    client = SessionManagementApiClient()
    print(json.dumps(client.set_debug_mode(args.vm_id, args.org_id, enabled=True)))


def disable_debug_mode_cli(args):
    """CLI wrapper for disabling debug mode on a VM"""
    client = SessionManagementApiClient()
    print(json.dumps(client.set_debug_mode(args.vm_id, args.org_id, enabled=False)))


def refresh_regions_cli(args):
    """CLI wrapper for refreshing cloud resources across all regions"""
    client = SessionManagementApiClient()
    client.refresh_regions()
    print("Successfully triggered a refresh of cloud resources across all regions.")


def configure_session_management_parser(parser: argparse.ArgumentParser):
    """Configure the CLI parser for session management commands"""
    vm_parser = parser.add_subparsers(
        description="Manage Virtual Machines via session management"
    )

    # vm list command
    vm_list_parser = vm_parser.add_parser("list", help="List VMs for an organization")
    vm_list_parser.add_argument(
        "--org-id",
        type=int,
        help="Organization ID to list VMs for; omit to list VMs without an organization",
    )
    vm_list_parser.set_defaults(func=list_vms_cli)

    # vm get command
    vm_get_parser = vm_parser.add_parser("get", help="Get a single VM")
    vm_get_parser.add_argument("vm_id", help="ID of the VM")
    vm_get_parser.add_argument(
        "--org-id", type=int, help="Organization ID the VM belongs to"
    )
    vm_get_parser.set_defaults(func=get_vm_cli)

    # vm create command
    vm_create_parser = vm_parser.add_parser(
        "create", help="Create a VM for yourself in an organization, and start it"
    )
    vm_create_parser.add_argument(
        "--org-id", type=int, required=True, help="Organization ID to create it in"
    )
    vm_create_parser.add_argument(
        "--region", required=True, help="Cloud region, e.g. eu-central-1"
    )
    vm_create_parser.add_argument(
        "--size", required=True, help="VM size name, see 'vms sizes'"
    )
    vm_create_parser.add_argument(
        "--expiration",
        required=True,
        help="Time until the VM is destroyed again, in format HH:MM:SS",
    )
    vm_create_parser.add_argument(
        "--image",
        help="Image, e.g. dev/latest, see 'vms images'; defaults to the region's default",
    )
    vm_create_parser.add_argument(
        "--debug-mode",
        action="store_true",
        help="Create it with debug mode on, opening its debug ports (RDP, WinRM)",
    )
    vm_create_parser.set_defaults(func=create_vm_cli)

    # vm destroy command
    vm_destroy_parser = vm_parser.add_parser("destroy", help="Destroy a VM")
    vm_destroy_parser.add_argument("vm_id", help="ID of the VM")
    vm_destroy_parser.add_argument(
        "--org-id", type=int, help="Organization ID the VM belongs to"
    )
    vm_destroy_parser.set_defaults(func=destroy_vm_cli)

    # vm sizes command
    vm_sizes_parser = vm_parser.add_parser(
        "sizes", help="List VM sizes and the regions they are available in"
    )
    vm_sizes_parser.set_defaults(func=list_vm_sizes_cli)

    # vm images command
    vm_images_parser = vm_parser.add_parser(
        "images", help="List VM images and the regions they are available in"
    )
    vm_images_parser.add_argument("--instance", help="Filter by instance, e.g. dev")
    vm_images_parser.add_argument("--version", help="Filter by version, e.g. 1.0.0")
    vm_images_parser.add_argument("--variant", help="Filter by variant")
    vm_images_parser.add_argument("--gpu-type", help="Filter by GPU type, e.g. l4")
    vm_images_parser.set_defaults(func=list_vm_images_cli)

    # vm extend-expiration command
    vm_extend_parser = vm_parser.add_parser(
        "extend-expiration", help="Extend the expiration time of a VM"
    )
    vm_extend_parser.add_argument("vm_id", help="ID of the VM to extend expiration for")
    vm_extend_parser.add_argument(
        "--org-id", type=int, required=True, help="Organization ID"
    )
    vm_extend_parser.add_argument(
        "--time", type=str, required=True, help="Extension timespan in format HH:MM:SS"
    )
    vm_extend_parser.set_defaults(func=extend_vm_expiration_cli)

    # vm enable-debug-mode / disable-debug-mode commands
    for name, func, help_text in (
        (
            "enable-debug-mode",
            enable_debug_mode_cli,
            "Enable debug mode on a VM, opening its debug ports (RDP, WinRM)",
        ),
        (
            "disable-debug-mode",
            disable_debug_mode_cli,
            "Disable debug mode on a VM, closing its debug ports again",
        ),
    ):
        debug_parser = vm_parser.add_parser(name, help=help_text)
        debug_parser.add_argument("vm_id", help="ID of the VM")
        debug_parser.add_argument(
            "--org-id", type=int, help="Organization ID the VM belongs to"
        )
        debug_parser.set_defaults(func=func)

    return vm_parser


def configure_regions_parser(parser: argparse.ArgumentParser):
    """Configure the CLI parser for region management commands"""
    regions_parser = parser.add_subparsers(
        description="Manage regions via session management"
    )

    # regions refresh command
    regions_refresh_parser = regions_parser.add_parser(
        "refresh",
        help="Force an immediate refresh of cached cloud resources across all regions",
    )
    regions_refresh_parser.set_defaults(func=refresh_regions_cli)

    return regions_parser


# Define CLI args for standalone usage
def configure_parser(parser):
    return configure_session_management_parser(parser)


if __name__ == "__main__":
    # Execute when the module is not initialized from an import statement.
    parser = argparse.ArgumentParser()
    configure_parser(parser)
    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
