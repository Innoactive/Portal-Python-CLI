# Innoactive Portal Python Client

Command-line client for Innoactive Portal's APIs, written in Python.

## Installation

To install it via pip (currently not published via pypi), run:

```sh
pip install portal-client@git+https://github.com/Innoactive/Portal-Backend-Python-Client.git@main
```

## Usage

```bash
$ innoactive-portal --help
usage: innoactive-portal [-h] {upload-app,upload-client} ...

positional arguments:
  {upload-app,upload-client}
                        Help on specific commands
    upload-app          Upload of applications / application versions to Portal
    upload-client       Upload of client applications to Portal

options:
  -h, --help            show this help message and exit
```
