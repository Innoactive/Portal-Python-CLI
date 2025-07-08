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
    def list_vms(self, organization_id):
        """
        List VMs for an organization
        """
        response = requests.get(
            urljoin(self.base_url, "/VirtualMachines"),
            headers={"Authorization": get_bearer_authorization_header()},
            params={"organization_id": organization_id},
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
            headers={"Authorization": get_bearer_authorization_header()},
            params={"organization_id": organization_id},
            json={"time": timespan},
            timeout=30,
        )

        if not response.ok:
            print(response.json())
        response.raise_for_status()

        return response.json()


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


def configure_session_management_parser(parser: argparse.ArgumentParser):
    """Configure the CLI parser for session management commands"""
    vm_parser = parser.add_subparsers(
        description="Manage Virtual Machines via session management"
    )

    # vm list command
    vm_list_parser = vm_parser.add_parser("list", help="List VMs for an organization")
    vm_list_parser.add_argument(
        "--org-id", type=int, required=True, help="Organization ID to list VMs for"
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


# Define CLI args for standalone usage
def configure_parser(parser):
    return configure_session_management_parser(parser)


def main(args):
    """Main function for standalone usage"""
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    # Execute when the module is not initialized from an import statement.
    args = configure_parser(parser=argparse.ArgumentParser()).parse_args()
    main(args)
