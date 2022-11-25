import json
from argparse import ArgumentParser
from urllib.parse import urljoin

import requests

from portal_client.application_uploader import (
    configure_parser as configure_app_upload_parser,
)
from portal_client.defaults import get_portal_backend_endpoint
from portal_client.organization import organization_parser
from portal_client.pagination import pagination_parser
from portal_client.utils import get_authorization_header


def list_applications(**filters):
    applications_url = urljoin(get_portal_backend_endpoint(), "/api/applications/")
    response = requests.get(
        applications_url,
        headers={"Authorization": get_authorization_header()},
        params=filters,
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def list_applications_cli(args):
    applications_response = list_applications(
        organization=args.organization,
        page=args.page,
        page_size=args.page_size,
        fulltext_search=args.search,
    )

    print(json.dumps(applications_response))


def upload_application_image(application_id, image_path):
    application_images_url = urljoin(
        get_portal_backend_endpoint(), f"/api/applications/{application_id}/images/"
    )
    response = requests.post(
        application_images_url,
        headers={"Authorization": get_authorization_header()},
        files={"image": open(image_path, "rb")},
    )

    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def upload_application_image_cli(args):
    users_response = upload_application_image(
        application_id=args.application, image_path=args.image
    )

    print(json.dumps(users_response))


def configure_applications_parser(parser: ArgumentParser):
    application_parser = parser.add_subparsers(
        description="List and manage applications on Portal"
    )

    applications_list_parser = application_parser.add_parser(
        "list",
        help="Returns a paginated list of applications on Portal",
        parents=[pagination_parser, organization_parser],
    )

    filters_group = applications_list_parser.add_argument_group(
        "filters", "Filtering Applications"
    )
    filters_group.add_argument(
        "--search",
        help="A search term (e.g. application name) to filter results by",
    )

    applications_list_parser.set_defaults(func=list_applications_cli)

    applications_upload_parser = application_parser.add_parser(
        "upload",
        help="Uploads an application to Portal",
    )
    configure_app_upload_parser(applications_upload_parser)

    application_images_parser = application_parser.add_parser(
        "images",
        help="List and manage application images on Portal",
    ).add_subparsers(description="List and manage application images on Portal")
    application_image_upload_parser = application_images_parser.add_parser(
        "upload", help="Upload an application image for an existing application"
    )
    application_image_upload_parser.add_argument(
        "image", help="Path to the image to be uploaded"
    )
    application_image_upload_parser.add_argument(
        "--application",
        metavar="APPLICATION_ID",
        help="ID of the existing application to upload an image for",
        required=True,
    )
    application_image_upload_parser.set_defaults(func=upload_application_image_cli)

    return application_parser
