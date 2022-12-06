# Innoactive Portal Python Client
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FInnoactive%2FPortal-Backend-Python-Client.svg?type=shield)](https://app.fossa.com/projects/git%2Bgithub.com%2FInnoactive%2FPortal-Backend-Python-Client?ref=badge_shield)


Command-line client for Innoactive Portal's APIs, written in Python.

## Installation

To install it via pip (currently not published via pypi), run:

```sh
pip install portal-client@git+https://github.com/Innoactive/Portal-Backend-Python-Client.git@main
```

## Usage

```bash
$ innoactive-portal --help
usage: innoactive-portal [-h] {upload-app,upload-client,users,groups} ...

positional arguments:
  {upload-app,upload-client,users,groups}
                        Help on specific commands
    upload-app          Upload of applications / application versions to Portal
    upload-client       Upload of client applications to Portal
    users               Manage user accounts on Portal
    groups              Manage user groups on Portal

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

## Examples

### Uploading a (new) application version

You will need the application's identity from Portal as well as the application archive (.zip or .apk) to be uploaded.

```sh
innoactive-portal upload-app \
./my-new-app-version.zip \ # application archive to be uploaded
--version 1.0.2 \ # version number of the new version
--tags tag1 tag2 \ # tags to be assigned to the application (version)
--organization-ids 1 2 3 \ # list of organization (ids) the application should be made available to
--name Test \ # the name of the application (version)
--identity 624 \ # the identity of the application this version belongs to
--current-version # whether or not the application version should be set as the current one
```

You can run `innoactive-portal upload-app --help` to get more information on available parameters.


## License
[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FInnoactive%2FPortal-Backend-Python-Client.svg?type=large)](https://app.fossa.com/projects/git%2Bgithub.com%2FInnoactive%2FPortal-Backend-Python-Client?ref=badge_large)