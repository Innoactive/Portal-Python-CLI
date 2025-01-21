import argparse

from .application_build_uploader import (
    configure_parser as configure_app_build_upload_parser,
)
from .applications_v1 import configure_applications_v1_parser
from .applications_v2 import configure_applications_v2_parser
from .branding import configure_branding_parser
from .client_application_uploader import (
    configure_parser as configure_client_application_parser,
)
from .organizations import configure_organizations_parser
from .usergroups import configure_user_groups_parser
from .users import configure_users_parser

## create the top-level parser
parser = argparse.ArgumentParser(prog="innoactive-portal")
subparsers = parser.add_subparsers(help="Help on specific commands")

applications_parser = subparsers.add_parser(
    "applications", help="Manage application builds (versions) on Portal"
)
# Create subparsers for each version under "applications"
applications_api_version_subparsers = applications_parser.add_subparsers(
    help="Help on specific commands"
)
# v1 parser
applications_v1_parser = applications_api_version_subparsers.add_parser("v1")
configure_applications_v1_parser(applications_v1_parser)
# configure_applications_v1_parser(applications_parser)

# v2 parser
applications_v2_parser = applications_api_version_subparsers.add_parser("v2")
configure_applications_v2_parser(applications_v2_parser)

application_build_upload_parser = subparsers.add_parser(
    "upload-app",
    help="Upload of application builds to Portal",
)
configure_app_build_upload_parser(application_build_upload_parser)

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
