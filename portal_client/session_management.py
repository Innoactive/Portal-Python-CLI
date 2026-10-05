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

    @staticmethod
    def _headers(organization_id=None):
        headers = {"Authorization": get_bearer_authorization_header()}
        if organization_id is not None:
            headers[ORGANIZATION_HEADER] = str(organization_id)
        return headers

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def list_vms(self, organization_id=None):
        """
        List VMs for an organization: the caller's own, or all of them for an
        organization admin. Without an organization, lists the VMs that belong to
        none, which needs the global list_virtual_machines permission.
        """
        response = requests.get(
            urljoin(self.base_url, "/VirtualMachines"),
            headers=self._headers(organization_id),
            timeout=30,
        )

        if not response.ok:
            print(response.json())
        response.raise_for_status()

        return response.json()

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def extend_vm_expiration(self, vm_id, organization_id, timespan):
        """
        Extend the expiration time of a VM
        """
        response = requests.put(
            urljoin(self.base_url, f"/VirtualMachines/{vm_id}/Expiration"),
            headers=self._headers(organization_id),
            json={"time": timespan},
            timeout=30,
        )

        if not response.ok:
            print(response.json())
        response.raise_for_status()

        return response.json()

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def refresh_regions(self):
        """
        Force an immediate refresh of the cached cloud resources (subnets,
        gateways, and VM images) across all regions, bypassing the configured
        cache expiry. Use after publishing a new VM image so it is picked up
        without waiting for the background refresh cycle. Admin only.
        """
        response = requests.post(
            urljoin(self.base_url, "/Regions/refresh"),
            headers={"Authorization": get_bearer_authorization_header()},
            timeout=30,
        )

        if not response.ok:
            print(response.text)
        response.raise_for_status()


def list_vms_cli(args):
    """CLI wrapper for listing VMs"""
    client = SessionManagementApiClient()
    vms_response = client.list_vms(organization_id=args.org_id)
    print(json.dumps(vms_response))


def extend_vm_expiration_cli(args):
    """CLI wrapper for extending VM expiration"""
    client = SessionManagementApiClient()
    response = client.extend_vm_expiration(
        vm_id=args.vm_id, organization_id=args.org_id, timespan=args.time
    )
    print(json.dumps(response))


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
