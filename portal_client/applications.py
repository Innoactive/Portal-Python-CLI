import json
from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.application_uploader import (
    configure_parser as configure_app_upload_parser,
)
from portal_client.defaults import get_portal_backend_endpoint
from portal_client.organization import organization_parser
from portal_client.pagination import pagination_parser
from portal_client.utils import get_authorization_header


def list_applications(**filters):
    users_url = urljoin(get_portal_backend_endpoint(), "/api/applications/")
    response = requests.get(
        users_url,
        headers={"Authorization": get_authorization_header()},
        params=filters,
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def list_applications_cli(args):
    users_response = list_applications(
        organization=args.organization,
        page=args.page,
        page_size=args.page_size,
        fulltext_search=args.search,
    )

    print(json.dumps(users_response))


def configure_applications_parser(parser: ArgumentParser):
    application_parser = parser.add_subparsers(
        description="List and manage applications on Portal"
    )

    applications_list_parser = application_parser.add_parser(
        "list",
        help="Returns a paginated list of applications on Portal",
        parents=[pagination_parser, organization_parser],
    )

    filters_group = applications_list_parser.add_argument_group(
        "filters", "Filtering Applications"
    )
    filters_group.add_argument(
        "--search",
        help="A search term (e.g. application name) to filter results by",
    )

    applications_list_parser.set_defaults(func=list_applications_cli)

    applications_upload_parser = application_parser.add_parser(
        "upload",
        help="Uploads an application to Portal",
    )
    configure_app_upload_parser(applications_upload_parser)

    return application_parser
