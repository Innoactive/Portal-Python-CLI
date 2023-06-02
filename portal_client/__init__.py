import argparse

from portal_client.application_uploader import (
    configure_parser as configure_application_parser,
)
from portal_client.applications import configure_applications_parser
from portal_client.branding import configure_branding_parser
from portal_client.client_application_uploader import (
    configure_parser as configure_client_application_parser,
)
from portal_client.organizations import configure_organizations_parser
from portal_client.usergroups import configure_user_groups_parser
from portal_client.users import configure_users_parser

## create the top-level parser
parser = argparse.ArgumentParser(prog="innoactive-portal")
subparsers = parser.add_subparsers(help="Help on specific commands")

applications_parser = subparsers.add_parser(
    "applications", help="Manage application versions on Portal"
)
configure_applications_parser(applications_parser)
application_parser = subparsers.add_parser(
    "upload-app", help="Upload of applications / application versions to Portal"
)
configure_application_parser(application_parser)

client_application_parser = subparsers.add_parser(
    "upload-client", help="Upload of client applications to Portal"
)
configure_client_application_parser(client_application_parser)

users_parser = subparsers.add_parser("users", help="Manage user accounts on Portal")
configure_users_parser(users_parser)

usergroups_parser = subparsers.add_parser("groups", help="Manage user groups on Portal")
configure_user_groups_parser(usergroups_parser)

branding_parser = subparsers.add_parser("branding", help="Manage branding on Portal")
configure_branding_parser(branding_parser)

organizations_parser = subparsers.add_parser(
    "organizations", help="Manage organizations on Portal"
)
configure_organizations_parser(organizations_parser)
