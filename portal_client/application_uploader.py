#!/usr/bin/env python
# Uploads an application based on provided config files.

import logging
import os
import requests
import os
import argparse
import sys
import backoff
from urllib.parse import urljoin

from portal_client.utils import get_authorization_header

from .portal_chunked_upload import ChunkedUploader

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
            url, data=app_data, headers={"Authorization": authorization_header}
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

        # publish the application
        return self.publish_application_data(
            application_url, authorization_header, config_parameters
        )


def configure_parser(parser):
    parser.add_argument("application-archive", help="path to the application archive")

    # single app config values:
    parser.add_argument("--name", help="How the application will be named on Portal.")
    parser.add_argument("--description", help="Short application description. ")
    parser.add_argument(
        "--version", help="Semantic application version.", required=True
    )
    parser.add_argument(
        "--type",
        help="Application type",
        default="other",
        choices=["unity", "unreal", "other"],
        required=True,
    )
    parser.add_argument(
        "--tags",
        help="List of tags to assign to the application.",
        nargs="+",
        type=str,
    )
    parser.add_argument("--application-identity", help="Identity name.")

    parser.add_argument(
        "--target-platform",
        help="Target platform. ",
        default="windows",
        choices=["windows", "android"],
        required=True,
    )
    parser.add_argument(
        "--current-version",
        help="Bool indicating if this version is the current version.",
    )
    parser.add_argument(
        "--executable-path", help="Path to the applications executable."
    )
    parser.add_argument("--package-name", help="Package name.")
    parser.add_argument("--panoramic-preview-image", help="360° preview image.")

    # single uploader config values:
    parser.add_argument(
        "--base-url", help="URL to the Portal Backend instance", required=True
    )
    # single uploader config values:
    parser.add_argument(
        "--organization-ids",
        nargs="+",
        type=str,
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

    config_parameters = {}

    # replace application config with passed args
    if not args.application_name is None:
        config_parameters["name"] = args.application_name

    if not args.application_description is None:
        config_parameters["description_html"] = args.application_description

    if not args.application_version is None:
        config_parameters["version"] = args.application_version

    if not args.application_identity is None:
        config_parameters["identity"] = args.application_identity

    if not args.current_version is None:
        config_parameters["current_version"] = args.current_version

    if not args.application_type is None:
        config_parameters["application_type"] = args.application_type

    if not args.tags is None:
        config_parameters["tags"] = args.tags

    if not args.target_platform is None:
        config_parameters["target_platform"] = args.target_platform

    if not args.package_name is None:
        config_parameters["package_name"] = args.package_name

    if not args.executable_path is None:
        config_parameters["executable_path"] = args.executable_path

    if not args.panoramic_preview_image is None:
        config_parameters["panoramic_preview_image"] = args.panoramic_preview_image

    # Validate application config
    if config_parameters.get("name") is None:
        print("Application name not provided. Cannot continue.")
        sys.exit(1)

    if (
        config_parameters.get("executable_path") is None
        and args.target_platform == "windows"
    ):
        print("'executable_path' name not provided. Cannot continue.")
        sys.exit(1)

    if config_parameters.get("version") is None:
        print("'version' name not provided. Cannot continue.")
        sys.exit(1)

    # Upload application
    uploader = ApplicationUploader(
        base_url=args.base_url, username=args.username, password=args.password
    )
    response = uploader.upload_application(application_archive, config_parameters)

    print("Finished upload with status: {}".format(response.status_code))
    if not response.ok:
        print(response.text)
        exit(1)


if __name__ == "__main__":
    args = configure_parser(parser=argparse.ArgumentParser()).parse_args()
    args.func(args)
