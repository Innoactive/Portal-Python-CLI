#!/usr/bin/env python
# Uploads an application based on provided config files.

import argparse
import logging
import os
import sys
from urllib.parse import urljoin

import backoff
import requests

from portal_client.defaults import PORTAL_BACKEND_ENDPOINT
from portal_client.portal_chunked_upload import ChunkedUploader
from portal_client.utils import get_authorization_header

logging.getLogger("backoff").addHandler(logging.StreamHandler())


class ApplicationUploader:
    """
    Class dealing with the upload of an application.
    """

    def __init__(self, base_url) -> None:
        self.base_url = base_url

    @backoff.on_exception(
        backoff.expo, requests.exceptions.ConnectionError, max_time=60
    )
    def publish_application_data(self, url, authorization_header, app_data):
        response = requests.post(
            url, json=app_data, headers={"Authorization": authorization_header}
        )

        return response

    def upload_application(self, application_file, config_parameters):

        application_url = urljoin(self.base_url, "/api/applications/")

        authorization_header = get_authorization_header()

        # upload chunked application
        uploader = ChunkedUploader(
            base_url=application_url, authorization_header=authorization_header
        )
        application_zip_url = uploader.upload_chunked_file(file_path=application_file)
        config_parameters["application_archive"] = application_zip_url

        # upload chunked panoramic image
        panoramic_image_path = config_parameters.get("panoramic_preview_image")
        if panoramic_image_path is not None:
            if not os.path.isfile(panoramic_image_path):
                panoramic_image_path = (
                    os.path.dirname(application_file) + "/" + panoramic_image_path
                )
            panoramic_image_url = uploader.upload_chunked_file(
                file_path=panoramic_image_path
            )
            config_parameters["panoramic_preview_image"] = panoramic_image_url

        # rewrite organization ids
        config_parameters["organizations"] = config_parameters.get(
            "organization_ids", []
        )
        del config_parameters["organization_ids"]

        # rewrite tags to be a comma separated list
        # config_parameters["tags"] = ",".join(config_parameters.get("tags", []))

        # publish the application
        return self.publish_application_data(
            application_url,
            authorization_header,
            config_parameters,
        )


def configure_parser(parser):
    parser.add_argument(
        "application_archive", help="Path to the application archive to be uploaded."
    )
    parser.add_argument(
        "--version", help="Semantic application version.", required=True
    )

    # single app config values:
    parser.add_argument(
        "--name", help="How the application will be named on Portal.", required=True
    )
    parser.add_argument("--description", help="Short application description. ")
    parser.add_argument(
        "--type",
        help="Application type",
        default="other",
        choices=["unity", "unreal", "other"],
    )
    parser.add_argument(
        "--tags",
        help="List of tags to assign to the application.",
        nargs="+",
        type=str,
    )
    parser.add_argument(
        "--identity",
        help='Identity of the application. Do not confuse this with the id of the application version, this is the original "id of the application". Each version will have the same identity, but a different id',
    )

    parser.add_argument(
        "--target-platform",
        help="Target platform. ",
        default="windows",
        choices=["windows", "android"],
    )
    parser.add_argument(
        "--current-version",
        help="Make this application version the current one. It will be rolled out to all clients. If no (application) identity is provided, this will be set to true automatically.",
        action="store_true",
    )
    parser.add_argument(
        "--executable-path", help="Path to the applications executable."
    )
    parser.add_argument("--package-name", help="Package name.")
    parser.add_argument("--panoramic-preview-image", help="360° preview image.")

    # single uploader config values:
    parser.add_argument(
        "--organization-ids",
        nargs="+",
        help="ID(s) of any organization the app should be available in.",
        required=True,
    )
    parser.set_defaults(func=main)
    return parser


def _validate_application_archive(application_archive):
    if application_archive is None:
        print("No valid application archive path specified. Cannot continue.")
        sys.exit(1)

    if not application_archive.endswith(".zip") and not application_archive.endswith(
        ".apk"
    ):
        print("application-path does not lead to a .zip or apk file. Cannot continue.")
        sys.exit(1)

    if not os.path.isfile(application_archive):
        print("no file found under {}. Cannot continue.".format(application_archive))
        sys.exit(1)


def main(args):

    application_archive = args.application_archive
    _validate_application_archive(application_archive)

    config_parameters = vars(args)
    del config_parameters["func"]

    # Upload application
    uploader = ApplicationUploader(base_url=PORTAL_BACKEND_ENDPOINT)
    response = uploader.upload_application(application_archive, config_parameters)

    print(response.text)
    if not response.ok:
        exit(1)


if __name__ == "__main__":
    args = configure_parser(parser=argparse.ArgumentParser()).parse_args()
    args.func(args)
