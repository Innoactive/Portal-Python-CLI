import argparse

from portal_client.application_uploader import (
    configure_parser as configure_application_parser,
)
from portal_client.client_application_uploader import (
    configure_parser as configure_client_application_parser,
)
from portal_client.users import configure_users_parser

## create the top-level parser
parser = argparse.ArgumentParser(prog="innoactive-portal")
subparsers = parser.add_subparsers(help="Help on specific commands")

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
