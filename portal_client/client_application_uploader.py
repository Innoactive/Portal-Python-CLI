#!/usr/bin/env python
# Uploads a client application based on provided CLI args

import argparse
import logging
from urllib.parse import urljoin

import backoff
import requests

from portal_client.defaults import get_portal_backend_endpoint
from portal_client.portal_chunked_upload import ChunkedUploader
from portal_client.utils import get_authorization_header

logging.getLogger("backoff").addHandler(logging.StreamHandler())


class ClientApplicationApiClient:
    """
    Class dealing with the client-applications API on the Portal Backend
    """

    def __init__(self, base_url) -> None:
        self.base_url = urljoin(base_url, "/api/client-applications/")

    def upload_version_binary(self, binary_path):
        # upload binary in chunks
        uploader = ChunkedUploader(
            base_url=self.base_url,
            authorization_header=get_authorization_header(),
        )
        return uploader.upload_chunked_file(file_path=binary_path)

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def create_client_application_version(self, slug, **version_data):
        return requests.post(
            urljoin(self.base_url, f"{slug}/versions/"),
            data=version_data,
            headers={"Authorization": get_authorization_header()},
        )

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def retrieve_client_application_version(self, slug, version):
        return requests.get(urljoin(self.base_url, f"{slug}/versions/{version}/"))

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def set_version_as_current(self, slug, version):
        return requests.patch(
            urljoin(self.base_url, f"{slug}/"),
            data={"current_version": version},
            headers={"Authorization": get_authorization_header()},
        )


# Define CLI args
def configure_parser(parser):
    parser.add_argument(
        "--slug",
        required=True,
        help="Slug identifying the client application on the server side, e.g. desktop-client, htc-vive-focus-3, oculus-quest, pico-neo-3-pro",
    )
    parser.add_argument(
        "--binary", required=True, help="path to the binary to be uploaded"
    )
    parser.add_argument(
        "--version",
        required=True,
        help="The semantic version of this new client application version",
    )
    parser.add_argument(
        "--mandatory",
        help="Whether or not an update to this new version will be mandatory.",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--changelog",
        help="Overview of changes in this version.",
    )
    parser.add_argument(
        "--current-version",
        help="Whether the newly uploaded version should set to be the current one.",
        default=False,
        action="store_true",
    )
    parser.set_defaults(func=main)
    return parser


def main(args):
    # Upload application
    client_applications_api = ClientApplicationApiClient(
        base_url=get_portal_backend_endpoint()
    )

    # Ensure the desired version doesn't exist yet
    check_response = client_applications_api.retrieve_client_application_version(
        args.slug, args.version
    )

    if check_response.status_code < 400:
        # the version already exists apparently. Aborting
        print(f"Version {args.version} already existing! Aborting.")
        print(check_response.text)
        exit(1)

    binary_url = client_applications_api.upload_version_binary(args.binary)
    response = client_applications_api.create_client_application_version(
        args.slug,
        version=args.version,
        binary=binary_url,
        mandatory=args.mandatory,
        changelog=args.changelog,
    )

    if args.current_version:
        response = client_applications_api.set_version_as_current(
            args.slug, args.version
        )
        response.raise_for_status()

    print(f"Finished upload with status: {response.status_code}")
    if not response.ok:
        print(response.text)
        exit(1)


if __name__ == "__main__":
    # Execute when the module is not initialized from an import statement.
    args = configure_parser(parser=argparse.ArgumentParser()).parse_args()
    args.func(args)
