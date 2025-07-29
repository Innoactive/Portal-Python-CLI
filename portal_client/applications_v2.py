import json
from argparse import ArgumentParser
import os
import tempfile
from tqdm import tqdm
from urllib.parse import urljoin

import requests

from portal_client.defaults import get_portal_backend_endpoint
from portal_client.organization import organization_parser
from portal_client.pagination import pagination_parser
from portal_client.portal_chunked_upload import ChunkedUploader
from portal_client.utils import get_authorization_header


def get_application(application_id):
    application_url = urljoin(
        get_portal_backend_endpoint(), f"/api/v2/applications/{application_id}/"
    )
    response = requests.get(
        application_url, headers={"Authorization": get_authorization_header()}
    )

    response.raise_for_status()

    return response.json()


def get_application_cli(args):
    application_response = get_application(args.id)
    print(json.dumps(application_response))


def list_applications(**filters):
    applications_url = urljoin(get_portal_backend_endpoint(), "/api/v2/applications/")
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


def get_application_build(build_id):
    application_build_url = urljoin(
        get_portal_backend_endpoint(), f"/api/v2/application-builds/{build_id}/"
    )
    response = requests.get(
        application_build_url,
        headers={"Authorization": get_authorization_header()},
    )

    response.raise_for_status()

    return response.json()


def get_application_build_cli(args):
    build_response = get_application_build(args.id)
    print(json.dumps(build_response))


def download_application_build(id, filepath=None):
    build_info = get_application_build(id)
    url = build_info.get("application_archive")
    if not url:
        raise ValueError("No URL found for the specified build ID.")

    if not filepath:
        filename = os.path.basename(url)
        temp_dir = os.path.join(tempfile.gettempdir(), "innoactive-portal", id)
        os.makedirs(temp_dir, exist_ok=True)
        target_path = os.path.join(temp_dir, filename)
    else:
        target_path = filepath

    response = requests.get(
        url, headers={"Authorization": get_authorization_header()}, stream=True
    )
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    with (
        open(target_path, "wb") as f,
        tqdm(
            desc=target_path, total=total, unit="iB", unit_scale=True, unit_divisor=1024
        ) as bar,
    ):
        for data in response.iter_content(chunk_size=1024):
            size = f.write(data)
            bar.update(size)

    return target_path


def download_application_build_cli(args):
    downloaded_file_path = download_application_build(args.id, args.filepath)
    print(downloaded_file_path)


def upload_application_build(
    application_archive, chunk_size_bytes, **application_build_data
):
    application_url = urljoin(
        get_portal_backend_endpoint(), "/api/v2/application-builds/"
    )

    authorization_header = get_authorization_header()

    # upload chunked application
    uploader = ChunkedUploader(
        base_url=application_url, authorization_header=authorization_header
    )
    application_zip_url = uploader.upload_chunked_file(
        file_path=application_archive, chunk_size_bytes=chunk_size_bytes
    )
    application_build_data["application_archive"] = application_zip_url

    # publish application build data
    response = requests.post(
        application_url,
        headers={"Authorization": authorization_header},
        json=application_build_data,
    )
    if not response.ok:
        print(response.json())
    response.raise_for_status()

    return response.json()


def upload_application_build_cli(args):
    build_data = vars(args)
    del build_data["func"]
    application_build_upload_response = upload_application_build(**build_data)
    print(json.dumps(application_build_upload_response))


def update_launch_configuration(application_id, platforms, build_id):
    authorization_header = get_authorization_header()
    body = {"application_build": build_id}

    responses = []
    for platform in platforms:
        url = urljoin(get_portal_backend_endpoint(),
                      f"/api/v2/applications/{application_id}/launch-configurations/{platform}/")
        response = requests.patch(url, headers={"Authorization": authorization_header}, json=body)
        if not response.ok:
            print(response.json())
        response.raise_for_status()
        responses.append(response.json())

    return responses


def update_launch_configuration_cli(args):
    update_launch_configuration_response = update_launch_configuration(
        application_id=args.id,
        platforms=args.xr_platforms,
        build_id=args.build_id
    )
    print(json.dumps(update_launch_configuration_response))


def _configure_applications_v2_get_parser(application_get_parser: ArgumentParser):
    application_get_parser.add_argument("id", help="ID of the application to get.")
    application_get_parser.set_defaults(func=get_application_cli)
    return application_get_parser


def _configure_applications_v2_list_parser(list_parser: ArgumentParser):
    filters_group = list_parser.add_argument_group("filters", "Filtering Applications")
    filters_group.add_argument(
        "--search",
        help="A search term (e.g. application name) to filter results by",
    )
    list_parser.set_defaults(func=list_applications_cli)

    return list_parser


def _configure_applications_v2_builds_parser(build_parser: ArgumentParser):
    build_subparsers = build_parser.add_subparsers(description="Build-related commands")

    get_subparser = build_subparsers.add_parser(
        "get", help="Get an application build by ID"
    )
    _configure_applications_v2_builds_get_subparser(get_subparser)

    upload_subparser = build_subparsers.add_parser("upload", help="Upload a new build")
    _configure_applications_v2_builds_upload_subparser(upload_subparser)

    download_subparser = build_subparsers.add_parser(
        "download", help="Download an application build"
    )
    _configure_applications_v2_builds_download_subparser(download_subparser)

    return build_parser


def _configure_applications_v2_update_launch_configuration_parser(update_launch_configuration_parser: ArgumentParser):
    update_launch_configuration_parser.add_argument(
        "id",
        help="ID of the application to update",
    )

    update_launch_configuration_parser.add_argument(
        "xr_platforms",
        help="Platforms to update the build for.",
        nargs="*",
        default=[],
        choices=["win-vr", "win-non-vr", "quest", "wave", "pico"],
    )

    update_launch_configuration_parser.add_argument(
        "build_id",
        help="ID of the build to set as current.",
    )

    update_launch_configuration_parser.set_defaults(func=update_launch_configuration_cli)


def _configure_applications_v2_builds_get_subparser(
    applications_get_build_parser: ArgumentParser,
):
    applications_get_build_parser.add_argument(
        "id",
        help="ID of the build to get.",
    )
    applications_get_build_parser.set_defaults(func=get_application_build_cli)


def _configure_applications_v2_builds_upload_subparser(
    applications_upload_build_parser: ArgumentParser,
):
    applications_upload_build_parser.add_argument(
        "application_archive",
        help="Path to the application archive / package to be uploaded.",
    )
    applications_upload_build_parser.add_argument(
        "--app-id",
        "--application-id",
        help="ID of the application to upload the build to.",
        required=True,
        dest="application",
    )
    applications_upload_build_parser.add_argument(
        "--version", help="Semantic application build version.", required=True
    )
    applications_upload_build_parser.add_argument(
        "--target-platform",
        help="Target platform. ",
        default="windows",
        choices=["windows", "android"],
    )
    applications_upload_build_parser.add_argument(
        "--executable-path", help="Path to the applications executable."
    )
    applications_upload_build_parser.add_argument(
        "--package-name", help="Package name."
    )
    applications_upload_build_parser.add_argument(
        "--xr-platform",
        "--supported-xr-platform",
        help="XR Platforms supported by the application.",
        nargs="+",
        default=[],
        choices=["win-vr", "win-non-vr", "quest", "wave", "pico"],
        dest="supported_xr_platforms",
        action="extend",
    )
    applications_upload_build_parser.add_argument(
        "--supports-arbitrary-cli-args",
        help="Whether or not the build supports arbitary cli args. Disable this to not send Portal's default args to the app.",
        default=True,
    )
    applications_upload_build_parser.add_argument(
        "--launch-args",
        "--launch-arguments",
        help="Launch arguments to be passed to the application.",
        dest="launch_args",
        default="",
    )
    applications_upload_build_parser.add_argument(
        "--changelog",
        help="Changelog for the build. Supports markdown",
        dest="changelog",
        default="",
    )

    applications_upload_build_parser.add_argument(
        "--chunk-size",
        help="Chunk size in bytes for the upload. Default is 2 MiB.",
        type=int,
        dest="chunk_size_bytes",
        default=2 * 1024 * 1024,
    )

    applications_upload_build_parser.set_defaults(func=upload_application_build_cli)


def _configure_applications_v2_builds_download_subparser(
    download_parser: ArgumentParser,
):
    download_parser.add_argument(
        "id",
        help="ID of the build to download.",
    )
    download_parser.add_argument(
        "--filepath",
        help="Path to save the downloaded file.",
    )

    download_parser.set_defaults(func=download_application_build_cli)


def configure_applications_v2_parser(parser: ArgumentParser):
    application_parser = parser.add_subparsers(
        description="List and manage applications on Portal"
    )

    # "applications v2 get <id>"
    get_parser = application_parser.add_parser("get", help="Get an application by ID")
    _configure_applications_v2_get_parser(get_parser)

    # "applications v2 list"
    list_parser = application_parser.add_parser(
        "list",
        help="Returns a paginated list of applications on Portal",
        parents=[pagination_parser, organization_parser],
    )
    _configure_applications_v2_list_parser(list_parser)

    # "applications v2 builds ..."
    builds_parser = application_parser.add_parser(
        "builds", help="Manage application builds"
    )
    _configure_applications_v2_builds_parser(builds_parser)

    # "applications v2 upload-build <args>"
    upload_build_parser = application_parser.add_parser(
        "upload-build",
        help="Upload a new application build, alias for 'builds upload'",
    )
    _configure_applications_v2_builds_upload_subparser(upload_build_parser)

    # "applications v2 update-launch-configuration <args>"
    update_launch_configuration_parser = application_parser.add_parser(
        "update-launch-configuration",
        help="Set current application build for platform"
    )
    _configure_applications_v2_update_launch_configuration_parser(update_launch_configuration_parser)

    return application_parser
