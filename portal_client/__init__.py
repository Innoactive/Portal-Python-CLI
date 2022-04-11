import argparse

from .application_uploader import configure_parser as configure_application_parser
from .client_application_uploader import (
    configure_parser as configure_client_application_parser,
)

## create the top-level parser
parser = argparse.ArgumentParser(prog="innoactive-portal")
subparsers = parser.add_subparsers(help="Help on specific commands")

# create the parser for the "a" command
application_parser = subparsers.add_parser(
    "upload-app", help="Upload of applications / application versions to Portal"
)
configure_application_parser(application_parser)

# create the parser for the "b" command
client_application_parser = subparsers.add_parser(
    "upload-client", help="Upload of client applications to Portal"
)
configure_client_application_parser(client_application_parser)
