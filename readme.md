# Innoactive Portal Python Client

Command-line client for Innoactive Portal's APIs, written in Python.

## Installation

To install it via pip (currently not published via pypi), run:

```sh
pip install portal-client@git+https://github.com/Innoactive/Portal-Python-CLI.git@main
```

## Usage

```bash
$ innoactive-portal --help
usage: innoactive-portal [-h] {applications,upload-app,upload-client,users,groups,branding,organizations,vm} ...

positional arguments:
  {applications,upload-app,upload-client,users,groups,branding,organizations,vm}
                        Help on specific commands
    applications        Manage application versions on Portal
    upload-app          Upload of applications / application versions to Portal
    upload-client       Upload of client applications to Portal
    users               Manage user accounts on Portal
    groups              Manage user groups on Portal
    branding            Manage branding on Portal
    organizations       Manage organizations on Portal
    vm                  Manage Virtual Machines

options:
  -h, --help            show this help message and exit
```

## Authentication

To authenticate against Portal Backend, you need to provide credentials as environment variables. You can use either a Bearer token issued by Portal or a user's username (email address) and password combination.

To use a bearer token, set:

```sh
export PORTAL_BACKEND_ACCESS_TOKEN=my-supersecure-token
```

To use a user's credentials use:

```sh
export PORTAL_BACKEND_USERNAME=jane.doe@example.org
export PORTAL_BACKEND_PASSWORD=supersecure-password
```

## Configuration

Apart from the authentication credentials, you can also opt to run the client against another Portal instance than the default, which is `https://api.innoactive.io`.

To use another Portal instance, set the environment variable like:

```sh
export PORTAL_BACKEND_ENDPOINT=https://my-portal-instance.example.org
```

For VM management, you can also configure the session management endpoint. The default is `https://session-management.innoactive.io`.

To use a different session management endpoint, set:

```sh
export PORTAL_SESSION_MANAGEMENT_ENDPOINT=https://my-session-mgmt.example.org
```

## Examples

### Uploading a (new) application build

You will need the application's identity from Portal as well as the application archive (.zip or .apk) to be uploaded.

```sh
innoactive-portal applications v2 upload-build \
./my-new-app-version.zip \ # application archive to be uploaded
--application-id 8feaa9c8-5aaf-4d49-8eef-0c20e8c73d9c \ # the id of the application this version belongs to
--version 1.0.2 \ # version number of the new version
--xr-platform win-non-vr \ # the XR platform this version is for, can be specified multiple times for multiple platforms
--launch-args='--my-custom-arg' \ # custom launch arguments for the application
--changelog='This version contains some bugfixes and new features' # changelog for the new version
```

You can run `innoactive-portal applications v2 upload-build --help` to get more information on available parameters.

## Development

To run the client locally, you can clone the repository and install the dependencies via uv:

```sh
git clone https://github.com/Innoactive/Portal-Python-CLI.git
cd Portal-Python-CLI
uv sync --locked
```

To run the client, you can use the `uv run` command:

```sh
uv run python -m portal_client --help
```
