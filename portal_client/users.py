from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.defaults import PORTAL_BACKEND_ENDPOINT
from portal_client.utils import get_authorization_header


def list_users(args):
    users_url = urljoin(PORTAL_BACKEND_ENDPOINT, "/api/users/")
    response = requests.get(
        users_url,
        headers={"Authorization": get_authorization_header()},
        params={
            "organization": args.organization,
            "groups": args.user_groups,
            "page": args.page,
            "page_size": args.page_size,
        },
    )

    print(response.text)


def configure_users_parser(parser: ArgumentParser):
    users_parser = parser.add_subparsers(
        description="List and manage user accounts on Portal"
    )

    users_list_parser = users_parser.add_parser(
        "list", help="Returns a paginated list of users on Portal"
    )
    pagination_group = users_list_parser.add_argument_group(
        "pagination", "Options for Pagination"
    )
    pagination_group.add_argument(
        "--page-size", type=int, help="How many results to return (per page)"
    )
    pagination_group.add_argument(
        "--page", type=int, help="The page of results to fetch (based on --page-size)"
    )

    filters_group = users_list_parser.add_argument_group("filters", "Filtering Users")
    filters_group.add_argument(
        "--user-groups",
        metavar="GROUP_ID",
        type=int,
        default=[],
        nargs="+",
        help="Only return users within the given groups (ids)",
    )
    filters_group.add_argument(
        "--organization",
        type=int,
        help="Only return users from the given organization (id)",
    )

    users_list_parser.set_defaults(func=list_users)
