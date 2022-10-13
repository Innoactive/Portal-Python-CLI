from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.defaults import PORTAL_BACKEND_ENDPOINT
from portal_client.pagination import pagination_parser
from portal_client.utils import get_authorization_header


def list_users(args):
    users_url = urljoin(PORTAL_BACKEND_ENDPOINT, "/api/groups/")
    response = requests.get(
        users_url,
        headers={"Authorization": get_authorization_header()},
        params={
            "organization": args.organization,
            "groups": args.user_groups,
            "page": args.page,
            "page_size": args.page_size,
            "search": args.search,
        },
    )

    print(response.text)


def configure_user_groups_parser(parser: ArgumentParser):
    usergroup_parser = parser.add_subparsers(
        description="List and manage user groups on Portal"
    )

    usergroup_list_parser = usergroup_parser.add_parser(
        "list",
        help="Returns a paginated list of user groups on Portal",
        parents=[pagination_parser],
    )

    filters_group = usergroup_list_parser.add_argument_group(
        "filters", "Filtering Users"
    )
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
    filters_group.add_argument(
        "--search",
        help="A search term (e.g. group name) to filter results by",
    )

    usergroup_list_parser.set_defaults(func=list_users)
