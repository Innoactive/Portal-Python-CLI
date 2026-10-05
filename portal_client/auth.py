#!/usr/bin/env python
# Interactive authentication for the Portal CLI via the OAuth2 authorization code flow.

import argparse
import hashlib
import json
import secrets
import time
import webbrowser
from base64 import urlsafe_b64encode
from http.server import BaseHTTPRequestHandler, HTTPServer
from os import getenv
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlparse

import requests

from .defaults import get_portal_backend_endpoint

# Portal runs Django OAuth Toolkit, which exposes these endpoints relative to the backend.
AUTHORIZATION_PATH = "/oauth/authorize/"
TOKEN_PATH = "/oauth/token/"

DEFAULT_REDIRECT_URI = "http://localhost:8723/callback"

# How long to wait for the user to complete the browser login, in seconds.
LOGIN_TIMEOUT = 300

# Refresh a stored access token this many seconds before it expires.
REFRESH_MARGIN = 60

# Environment variables used to configure the OAuth client (see resolve_login_settings).
CLIENT_ID_ENV = "PORTAL_BACKEND_CLIENT_ID"
CLIENT_SECRET_ENV = "PORTAL_BACKEND_CLIENT_SECRET"
REDIRECT_URI_ENV = "PORTAL_BACKEND_REDIRECT_URI"
SCOPE_ENV = "PORTAL_BACKEND_OAUTH_SCOPE"


def _config_dir() -> Path:
    """Directory holding the CLI's config and credentials, respecting XDG_CONFIG_HOME."""
    config_home = getenv("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "innoactive-portal"


def _config_path() -> Path:
    """Location of the optional config file (client_id, client_secret, ...)."""
    return _config_dir() / "config.json"


def _credentials_path() -> Path:
    """Location of the persisted credentials file."""
    return _config_dir() / "credentials.json"


def load_config() -> dict:
    """Load the optional config file, or an empty dict if there is none."""
    try:
        return json.loads(_config_path().read_text())
    except (FileNotFoundError, ValueError):
        return {}


def resolve_login_settings(
    client_id: str | None = None,
    client_secret: str | None = None,
    redirect_uri: str | None = None,
    scope: str | None = None,
) -> dict:
    """Resolve OAuth client settings from CLI args, env vars and the config file.

    Precedence for each setting is: explicit argument (CLI flag) > environment variable
    > config file > built-in default.
    """
    config = load_config()
    return {
        "client_id": client_id or getenv(CLIENT_ID_ENV) or config.get("client_id"),
        "client_secret": client_secret
        or getenv(CLIENT_SECRET_ENV)
        or config.get("client_secret"),
        "redirect_uri": redirect_uri
        or getenv(REDIRECT_URI_ENV)
        or config.get("redirect_uri")
        or DEFAULT_REDIRECT_URI,
        "scope": scope or getenv(SCOPE_ENV) or config.get("scope"),
    }


def save_credentials(credentials: dict) -> Path:
    """Persist credentials to disk with owner-only permissions."""
    path = _credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(credentials, indent=2))
    # Restrict access to the current user only, this file holds an access token.
    path.chmod(0o600)
    return path


def load_credentials() -> dict | None:
    """Load persisted credentials, or None if there are none (or they are unreadable)."""
    path = _credentials_path()
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError):
        return None


def clear_credentials() -> bool:
    """Remove any persisted credentials. Returns True if a file was removed."""
    path = _credentials_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def get_stored_access_token() -> str | None:
    """Return the access token from persisted credentials, if any.

    An expired (or nearly expired) token is first renewed with the stored refresh
    token, so a single login lasts as long as the refresh token does.
    """
    credentials = load_credentials()
    if not credentials:
        return None
    expires_at = credentials.get("expires_at")
    if (
        expires_at
        and time.time() >= expires_at - REFRESH_MARGIN
        and credentials.get("refresh_token")
        and credentials.get("client_id")
    ):
        credentials = refresh_access_token(credentials)
    return credentials.get("access_token")


def _credentials_from_token_response(
    token_response: dict, endpoint: str, client_id: str, refresh_token: str | None
) -> dict:
    """Build the persisted credentials from a token endpoint response."""
    credentials = {
        "access_token": token_response["access_token"],
        "token_type": token_response.get("token_type", "Bearer"),
        "scope": token_response.get("scope"),
        "endpoint": endpoint,
        # Kept so the token can be refreshed without the user logging in again.
        "client_id": client_id,
        "refresh_token": token_response.get("refresh_token", refresh_token),
    }
    expires_in = token_response.get("expires_in")
    if expires_in:
        credentials["expires_at"] = time.time() + expires_in
    return credentials


def refresh_access_token(credentials: dict) -> dict:
    """Trade the stored refresh token for a new access token and persist it."""
    client_id = credentials["client_id"]
    # A confidential client's secret is never stored; it comes from env or config.
    client_secret = resolve_login_settings()["client_secret"]
    response = requests.post(
        urljoin(credentials["endpoint"], TOKEN_PATH),
        data={
            "grant_type": "refresh_token",
            "refresh_token": credentials["refresh_token"],
            "client_id": client_id,
        },
        auth=(client_id, client_secret) if client_secret else None,
        timeout=30,
    )

    if not response.ok:
        raise Exception(
            "Refreshing the access token failed (HTTP {}): {}. Run "
            "'innoactive-portal auth login' again.".format(
                response.status_code, response.text
            )
        )

    refreshed = _credentials_from_token_response(
        response.json(), credentials["endpoint"], client_id, credentials["refresh_token"]
    )
    save_credentials(refreshed)
    return refreshed


def generate_pkce_pair() -> tuple[str, str]:
    """Generate a PKCE (code_verifier, code_challenge) pair using the S256 method."""
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def build_authorization_url(
    endpoint: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    code_challenge: str,
    scope: str | None = None,
) -> str:
    """Build the OAuth2 authorization URL to open in the browser."""
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    if scope:
        params["scope"] = scope
    return urljoin(endpoint, AUTHORIZATION_PATH) + "?" + urlencode(params)


def exchange_code_for_token(
    endpoint: str,
    client_id: str,
    code: str,
    redirect_uri: str,
    code_verifier: str,
    client_secret: str | None = None,
) -> dict:
    """Exchange an authorization code for an access token at the token endpoint."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    # Confidential clients authenticate with HTTP Basic; public clients send only client_id.
    auth = (client_id, client_secret) if client_secret else None
    response = requests.post(
        urljoin(endpoint, TOKEN_PATH), data=data, auth=auth, timeout=30
    )

    if not response.ok:
        raise Exception(
            "Token exchange failed (HTTP {}): {}".format(
                response.status_code, response.text
            )
        )

    return response.json()


class _CallbackHandler(BaseHTTPRequestHandler):
    """Handles the single redirect request from the authorization server."""

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        # Ignore unrelated requests (e.g. favicon) until we see the OAuth response.
        if "code" not in query and "error" not in query:
            self.send_response(404)
            self.end_headers()
            return

        self.server.auth_response = {  # type: ignore[attr-defined]
            "code": query.get("code", [None])[0],
            "state": query.get("state", [None])[0],
            "error": query.get("error", [None])[0],
            "error_description": query.get("error_description", [None])[0],
        }

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        message = (
            "Authentication failed. You can close this window and return to the terminal."
            if query.get("error")
            else "Authentication successful. You can close this window and return to the terminal."
        )
        self.wfile.write(
            "<html><body><h2>{}</h2></body></html>".format(message).encode("utf-8")
        )

    def log_message(self, *args):
        # Silence the default per-request logging to stderr.
        pass


def _wait_for_callback(redirect_uri: str, timeout: int) -> dict:
    """Run a local HTTP server until the authorization server redirects back to it."""
    parsed = urlparse(redirect_uri)
    host = parsed.hostname or "localhost"
    port = parsed.port or 80

    httpd = HTTPServer((host, port), _CallbackHandler)
    httpd.auth_response = None  # type: ignore[attr-defined]
    httpd.timeout = timeout

    deadline = time.monotonic() + timeout
    while httpd.auth_response is None:  # type: ignore[attr-defined]
        if time.monotonic() >= deadline:
            httpd.server_close()
            raise Exception(
                "Timed out waiting for the authentication callback after {} seconds.".format(
                    timeout
                )
            )
        httpd.handle_request()

    httpd.server_close()
    return httpd.auth_response  # type: ignore[attr-defined]


def login(
    client_id: str,
    client_secret: str | None = None,
    endpoint: str | None = None,
    redirect_uri: str = DEFAULT_REDIRECT_URI,
    scope: str | None = None,
    open_browser: bool = True,
) -> dict:
    """Run the interactive authorization code flow and persist the resulting token.

    Opens the browser to the authorization endpoint, catches the redirect on a local
    server, exchanges the returned code for an access token and stores it. Returns the
    token response from the server.
    """
    endpoint = endpoint or get_portal_backend_endpoint()
    code_verifier, code_challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(16)

    authorization_url = build_authorization_url(
        endpoint, client_id, redirect_uri, state, code_challenge, scope
    )

    print("Opening your browser to sign in to {}".format(endpoint))
    print(
        "If it does not open automatically, visit this URL:\n{}\n".format(
            authorization_url
        )
    )
    if open_browser:
        webbrowser.open(authorization_url)

    response = _wait_for_callback(redirect_uri, LOGIN_TIMEOUT)

    if response.get("error"):
        raise Exception(
            "Authorization failed: {} - {}".format(
                response["error"], response.get("error_description") or ""
            ).strip(" -")
        )

    if response.get("state") != state:
        raise Exception(
            "State mismatch in authorization response, aborting for security reasons."
        )

    token_response = exchange_code_for_token(
        endpoint,
        client_id,
        response["code"],
        redirect_uri,
        code_verifier,
        client_secret,
    )

    save_credentials(
        _credentials_from_token_response(token_response, endpoint, client_id, None)
    )
    return token_response


def login_cli(args):
    """CLI wrapper for the interactive login command."""
    settings = resolve_login_settings(
        client_id=args.client_id,
        client_secret=args.client_secret,
        redirect_uri=args.redirect_uri,
        scope=args.scope,
    )

    if not settings["client_id"]:
        print(
            "No OAuth client ID provided. Pass --client-id, set {} or add "
            '"client_id" to {}.'.format(CLIENT_ID_ENV, _config_path())
        )
        raise SystemExit(1)

    try:
        login(
            client_id=settings["client_id"],
            client_secret=settings["client_secret"],
            redirect_uri=settings["redirect_uri"],
            scope=settings["scope"],
            open_browser=not args.no_browser,
        )
    except Exception as error:
        print("Login failed: {}".format(error))
        raise SystemExit(1)

    print("Login successful. Credentials saved to {}".format(_credentials_path()))


def logout_cli(args):
    """CLI wrapper for clearing stored credentials."""
    if clear_credentials():
        print("Logged out, stored credentials removed.")
    else:
        print("No stored credentials to remove.")


def status_cli(args):
    """CLI wrapper for showing the current authentication status."""
    credentials = load_credentials()
    if not credentials:
        print("Not logged in. Run 'innoactive-portal auth login' to authenticate.")
        return

    print("Logged in to {}".format(credentials.get("endpoint", "unknown endpoint")))
    expires_at = credentials.get("expires_at")
    if expires_at:
        remaining = expires_at - time.time()
        if remaining <= 0 and credentials.get("refresh_token"):
            print("Access token has expired, it is refreshed on the next request.")
        elif remaining <= 0:
            print("Access token has expired, run 'innoactive-portal auth login' again.")
        else:
            print("Access token expires in {} minutes.".format(int(remaining // 60)))


def configure_auth_parser(parser: argparse.ArgumentParser):
    """Configure the CLI parser for authentication commands."""
    auth_subparsers = parser.add_subparsers(
        description="Authenticate against Portal"
    )

    login_parser = auth_subparsers.add_parser(
        "login", help="Log in interactively via the browser (authorization code flow)"
    )
    # These default to None so resolve_login_settings() can fall back to the
    # PORTAL_BACKEND_* env vars and the config file before the built-in defaults.
    login_parser.add_argument(
        "--client-id",
        default=None,
        help="OAuth client ID of the application registered on Portal "
        "(falls back to ${} or the config file)".format(CLIENT_ID_ENV),
    )
    login_parser.add_argument(
        "--client-secret",
        default=None,
        help="OAuth client secret for confidential clients; omit for public clients "
        "(falls back to ${} or the config file)".format(CLIENT_SECRET_ENV),
    )
    login_parser.add_argument(
        "--redirect-uri",
        default=None,
        help="Redirect URI registered for the OAuth client "
        "(falls back to ${} or the config file; default: {})".format(
            REDIRECT_URI_ENV, DEFAULT_REDIRECT_URI
        ),
    )
    login_parser.add_argument(
        "--scope",
        default=None,
        help="Space-separated OAuth scopes to request, optional "
        "(falls back to ${} or the config file)".format(SCOPE_ENV),
    )
    login_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Do not open the browser automatically, just print the authorization URL",
    )
    login_parser.set_defaults(func=login_cli)

    logout_parser = auth_subparsers.add_parser(
        "logout", help="Remove stored credentials"
    )
    logout_parser.set_defaults(func=logout_cli)

    status_parser = auth_subparsers.add_parser(
        "status", help="Show the current authentication status"
    )
    status_parser.set_defaults(func=status_cli)

    return auth_subparsers
