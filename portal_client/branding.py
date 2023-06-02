import argparse
import json
from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.defaults import get_portal_backend_endpoint
from portal_client.utils import get_authorization_header


def get_branding(organization_id=None):
    branding_url = urljoin(get_portal_backend_endpoint(), "/api/branding/")
    response = requests.get(
        branding_url,
        headers={"Authorization": get_authorization_header()},
        params={"organization": organization_id},
        timeout=5,
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def get_branding_cli(args):
    branding_response = get_branding(
        organization_id=args.organization,
    )

    print(json.dumps(branding_response))


def update_branding(organization_id, **kwargs):
    # split files from normal kwargs
    files = {}
    for key in ["logo", "product_icon", "app_image_placeholder"]:
        if key in kwargs:
            files[key] = kwargs.pop(key)
    branding_url = urljoin(get_portal_backend_endpoint(), "/api/branding/")
    response = requests.put(
        branding_url,
        data=kwargs,
        headers={"Authorization": get_authorization_header()},
        params={"organization": organization_id},
        files=files,
        timeout=30,
    )

    if not response.ok:
        print(response.text)
    response.raise_for_status()

    return response.json()


def update_branding_cli(args):
    changed_args = {
        k: v
        for k, v in vars(args).items()
        if v is not None and k != "func" and k != "organization"
    }
    branding_response = update_branding(
        organization_id=args.organization,
        **changed_args,
    )

    print(json.dumps(branding_response))


base_branding_parser = ArgumentParser(add_help=False)
base_branding_parser.add_argument(
    "organization",
    type=int,
    help="The organization (id) for which to obrtain / manage branding",
)


def configure_branding_parser(parser: ArgumentParser):
    branding_parser = parser.add_subparsers(
        description="Obtain and manage branding on Portal"
    )

    branding_get_parser = branding_parser.add_parser(
        "get",
        help="Returns branding for a given organization",
        parents=[base_branding_parser],
    )
    branding_get_parser.set_defaults(func=get_branding_cli)

    branding_update_parser = branding_parser.add_parser(
        "update",
        help="Update branding for a given organization",
        parents=[base_branding_parser],
    )
    branding_update_parser.add_argument(
        "--background-color", type=str, help="Background Color", dest="background"
    )
    branding_update_parser.add_argument(
        "--primary-color", type=str, help="Primary / Brand Color", dest="primary"
    )
    branding_update_parser.add_argument(
        "--logo", type=argparse.FileType("rb"), help="Brand logo"
    )
    branding_update_parser.add_argument(
        "--icon", type=argparse.FileType("rb"), help="Brand icon", dest="product_icon"
    )
    branding_update_parser.add_argument(
        "--app-image-placeholder",
        type=argparse.FileType("rb"),
        help="Placeholder image for applications",
    )
    branding_update_parser.add_argument("--company-name", type=str, help="Company name")
    branding_update_parser.add_argument("--product-name", type=str, help="Portal name")
    branding_update_parser.set_defaults(func=update_branding_cli)

    return branding_parser
