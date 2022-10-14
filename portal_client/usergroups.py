import json
from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.defaults import get_portal_backend_endpoint
from portal_client.pagination import pagination_parser
from portal_client.utils import get_authorization_header


def list_usergroups(**filters):
    users_url = urljoin(get_portal_backend_endpoint(), "/api/groups/")
    response = requests.get(
        users_url,
        headers={"Authorization": get_authorization_header()},
        params=filters,
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def list_usergroups_cli(args):
    user_list_response = list_usergroups(
        organization=args.organization,
        groups=args.user_groups,
        page=args.page,
        page_size=args.page_size,
        search=args.search,
    )
    print(json.dumps(user_list_response))


def add_users_to_group(group, users):
    maange_users_within_group_url = urljoin(
        get_portal_backend_endpoint(), f"/api/groups/{group}/users/"
    )
    response = requests.post(
        maange_users_within_group_url,
        headers={"Authorization": get_authorization_header()},
        json={"users": users},
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.ok


def add_users_to_group_cli(args):
    add_user_to_group_response = add_users_to_group(group=args.group, users=args.users)
    print(
        "User(s) added to group successfully."
        if add_user_to_group_response
        else "Failed adding user(s) to group."
    )


def remove_user_from_group(group, user):
    maange_users_within_group_url = urljoin(
        get_portal_backend_endpoint(), f"/api/groups/{group}/users/{user}"
    )
    response = requests.delete(
        maange_users_within_group_url,
        headers={"Authorization": get_authorization_header()},
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.ok


def remove_users_from_group_cli(args):
    remove_user_from_group_response = remove_user_from_group(
        group=args.group, user=args.user
    )
    print(
        "User removed from group successfully."
        if remove_user_from_group_response
        else "Failed removing user from group."
    )


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

    usergroup_list_parser.set_defaults(func=list_usergroups_cli)

    usergroup_add_users_parser = usergroup_parser.add_parser(
        "add-users", help="Adds users to a user group."
    )
    usergroup_add_users_parser.add_argument(
        "group", metavar="GROUP_ID", help="The user group (id) to add users to."
    )
    usergroup_add_users_parser.add_argument(
        "users",
        nargs="+",
        metavar="USER_ID",
        help="IDs of users to be added to the user group.",
    )
    usergroup_add_users_parser.set_defaults(func=add_users_to_group_cli)

    usergroup_remove_user_parser = usergroup_parser.add_parser(
        "remove-user", help="Removes a user from a user group."
    )
    usergroup_remove_user_parser.add_argument(
        "group", metavar="GROUP_ID", help="The user group (id) to remove the user from."
    )
    usergroup_remove_user_parser.add_argument(
        "user",
        metavar="USER_ID",
        help="ID of user to be removed from the user group.",
    )
    usergroup_remove_user_parser.set_defaults(func=remove_users_from_group_cli)

    return usergroup_parser
