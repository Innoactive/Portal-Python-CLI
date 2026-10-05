import hashlib
import time
from base64 import urlsafe_b64encode
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import pytest

from portal_client import auth


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    """Point the credentials file at a throwaway directory for each test."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path / "innoactive-portal" / "credentials.json"


class TestPKCE:
    def test_generate_pkce_pair_matches_s256(self):
        verifier, challenge = auth.generate_pkce_pair()

        expected = (
            urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest())
            .rstrip(b"=")
            .decode("ascii")
        )
        assert challenge == expected
        # Challenge must be URL-safe base64 without padding.
        assert "=" not in challenge

    def test_generate_pkce_pair_is_random(self):
        assert auth.generate_pkce_pair()[0] != auth.generate_pkce_pair()[0]


class TestAuthorizationUrl:
    def test_build_authorization_url_contains_expected_params(self):
        url = auth.build_authorization_url(
            endpoint="https://api.innoactive.io",
            client_id="my-client",
            redirect_uri="http://localhost:8723/callback",
            state="state123",
            code_challenge="challenge123",
            scope="read write",
        )

        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        assert parsed.path == "/oauth/authorize/"
        assert query["response_type"] == ["code"]
        assert query["client_id"] == ["my-client"]
        assert query["redirect_uri"] == ["http://localhost:8723/callback"]
        assert query["state"] == ["state123"]
        assert query["code_challenge"] == ["challenge123"]
        assert query["code_challenge_method"] == ["S256"]
        assert query["scope"] == ["read write"]

    def test_build_authorization_url_omits_scope_when_absent(self):
        url = auth.build_authorization_url(
            endpoint="https://api.innoactive.io",
            client_id="my-client",
            redirect_uri="http://localhost:8723/callback",
            state="state123",
            code_challenge="challenge123",
        )
        assert "scope" not in parse_qs(urlparse(url).query)


class TestTokenExchange:
    def test_exchange_code_for_public_client(self, requests_mock):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"access_token": "abc", "token_type": "Bearer"},
        )

        result = auth.exchange_code_for_token(
            endpoint="https://api.innoactive.io",
            client_id="public-client",
            code="the-code",
            redirect_uri="http://localhost:8723/callback",
            code_verifier="verifier",
        )

        assert result["access_token"] == "abc"
        body = parse_qs(requests_mock.last_request.text)
        assert body["grant_type"] == ["authorization_code"]
        assert body["code"] == ["the-code"]
        assert body["client_id"] == ["public-client"]
        assert body["code_verifier"] == ["verifier"]
        # Public clients must not send an Authorization (Basic) header.
        assert "Authorization" not in requests_mock.last_request.headers

    def test_exchange_code_for_confidential_client_uses_basic_auth(
        self, requests_mock
    ):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"access_token": "abc", "token_type": "Bearer"},
        )

        auth.exchange_code_for_token(
            endpoint="https://api.innoactive.io",
            client_id="confidential-client",
            code="the-code",
            redirect_uri="http://localhost:8723/callback",
            code_verifier="verifier",
            client_secret="s3cr3t",
        )

        assert requests_mock.last_request.headers["Authorization"].startswith("Basic ")

    def test_exchange_code_raises_on_error(self, requests_mock):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"error": "invalid_grant"},
            status_code=400,
        )

        with pytest.raises(Exception, match="Token exchange failed"):
            auth.exchange_code_for_token(
                endpoint="https://api.innoactive.io",
                client_id="public-client",
                code="bad-code",
                redirect_uri="http://localhost:8723/callback",
                code_verifier="verifier",
            )


class TestCredentials:
    def test_save_and_load_roundtrip(self, isolated_config):
        auth.save_credentials({"access_token": "stored-token"})

        assert isolated_config.exists()
        assert auth.load_credentials()["access_token"] == "stored-token"
        assert auth.get_stored_access_token() == "stored-token"
        # File must be readable/writable by the owner only.
        assert isolated_config.stat().st_mode & 0o777 == 0o600

    def test_load_returns_none_without_file(self, isolated_config):
        assert auth.load_credentials() is None
        assert auth.get_stored_access_token() is None

    def test_clear_credentials(self, isolated_config):
        auth.save_credentials({"access_token": "stored-token"})
        assert auth.clear_credentials() is True
        assert auth.get_stored_access_token() is None
        # Clearing again when nothing is stored is a no-op.
        assert auth.clear_credentials() is False


class TestSettingsResolution:
    def test_flag_takes_precedence_over_env_and_config(
        self, isolated_config, monkeypatch
    ):
        monkeypatch.setenv("PORTAL_BACKEND_CLIENT_ID", "env-client")
        auth.save_credentials({})  # ensure the config dir exists
        auth._config_path().write_text('{"client_id": "config-client"}')

        settings = auth.resolve_login_settings(client_id="flag-client")
        assert settings["client_id"] == "flag-client"

    def test_env_takes_precedence_over_config(self, isolated_config, monkeypatch):
        monkeypatch.setenv("PORTAL_BACKEND_CLIENT_ID", "env-client")
        auth.save_credentials({})
        auth._config_path().write_text('{"client_id": "config-client"}')

        assert auth.resolve_login_settings()["client_id"] == "env-client"

    def test_falls_back_to_config_file(self, isolated_config, monkeypatch):
        monkeypatch.delenv("PORTAL_BACKEND_CLIENT_ID", raising=False)
        monkeypatch.delenv("PORTAL_BACKEND_CLIENT_SECRET", raising=False)
        auth.save_credentials({})
        auth._config_path().write_text(
            '{"client_id": "config-client", "client_secret": "config-secret", '
            '"scope": "read", "redirect_uri": "http://localhost:9000/cb"}'
        )

        settings = auth.resolve_login_settings()
        assert settings["client_id"] == "config-client"
        assert settings["client_secret"] == "config-secret"
        assert settings["scope"] == "read"
        assert settings["redirect_uri"] == "http://localhost:9000/cb"

    def test_redirect_uri_defaults_when_unset(self, isolated_config, monkeypatch):
        monkeypatch.delenv("PORTAL_BACKEND_REDIRECT_URI", raising=False)
        assert (
            auth.resolve_login_settings()["redirect_uri"] == auth.DEFAULT_REDIRECT_URI
        )

    def test_missing_config_file_is_empty(self, isolated_config):
        assert auth.load_config() == {}


class TestLoginFlow:
    def test_login_persists_access_token(self, requests_mock, isolated_config):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={
                "access_token": "the-access-token",
                "token_type": "Bearer",
                "scope": "read",
                "expires_in": 3600,
            },
        )

        with patch(
            "portal_client.auth.secrets.token_urlsafe",
            side_effect=["fake-verifier", "fake-state"],
        ), patch(
            "portal_client.auth._wait_for_callback",
            return_value={"code": "auth-code", "state": "fake-state", "error": None},
        ):
            token_response = auth.login(
                client_id="my-client",
                endpoint="https://api.innoactive.io",
                open_browser=False,
            )

        assert token_response["access_token"] == "the-access-token"
        # Token is persisted and the PKCE verifier is sent in the exchange.
        assert auth.get_stored_access_token() == "the-access-token"
        body = parse_qs(requests_mock.last_request.text)
        assert body["code_verifier"] == ["fake-verifier"]
        assert body["code"] == ["auth-code"]

    def test_login_rejects_state_mismatch(self, requests_mock, isolated_config):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"access_token": "should-not-be-used"},
        )

        with patch(
            "portal_client.auth.secrets.token_urlsafe",
            side_effect=["fake-verifier", "expected-state"],
        ), patch(
            "portal_client.auth._wait_for_callback",
            return_value={"code": "auth-code", "state": "tampered", "error": None},
        ):
            with pytest.raises(Exception, match="State mismatch"):
                auth.login(
                    client_id="my-client",
                    endpoint="https://api.innoactive.io",
                    open_browser=False,
                )

        assert auth.get_stored_access_token() is None

    def test_login_raises_on_authorization_error(self, isolated_config):
        with patch(
            "portal_client.auth.secrets.token_urlsafe",
            side_effect=["fake-verifier", "fake-state"],
        ), patch(
            "portal_client.auth._wait_for_callback",
            return_value={
                "code": None,
                "state": None,
                "error": "access_denied",
                "error_description": "user said no",
            },
        ):
            with pytest.raises(Exception, match="access_denied"):
                auth.login(
                    client_id="my-client",
                    endpoint="https://api.innoactive.io",
                    open_browser=False,
                )


class TestTokenRefresh:
    def test_login_keeps_refresh_token_and_client(self, requests_mock, isolated_config):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600},
        )

        with patch(
            "portal_client.auth._wait_for_callback",
            return_value={"code": "c", "state": "s", "error": None},
        ), patch("portal_client.auth.secrets.token_urlsafe", side_effect=["v", "s"]):
            auth.login(
                client_id="my-client",
                endpoint="https://api.innoactive.io",
                open_browser=False,
            )

        stored = auth.load_credentials()
        assert stored["refresh_token"] == "r1"
        assert stored["client_id"] == "my-client"

    def test_valid_token_is_not_refreshed(self, requests_mock, isolated_config):
        auth.save_credentials(
            {
                "access_token": "a1",
                "refresh_token": "r1",
                "client_id": "my-client",
                "endpoint": "https://api.innoactive.io",
                "expires_at": time.time() + 3600,
            }
        )

        assert auth.get_stored_access_token() == "a1"
        assert not requests_mock.called

    def test_expired_token_is_refreshed_and_persisted(
        self, requests_mock, isolated_config, monkeypatch
    ):
        monkeypatch.delenv("PORTAL_BACKEND_CLIENT_SECRET", raising=False)
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"access_token": "a2", "refresh_token": "r2", "expires_in": 3600},
        )
        auth.save_credentials(
            {
                "access_token": "a1",
                "refresh_token": "r1",
                "client_id": "my-client",
                "endpoint": "https://api.innoactive.io",
                "expires_at": time.time() - 1,
            }
        )

        assert auth.get_stored_access_token() == "a2"
        body = parse_qs(requests_mock.last_request.text)
        assert body == {
            "grant_type": ["refresh_token"],
            "refresh_token": ["r1"],
            "client_id": ["my-client"],
        }
        # The rotated refresh token replaces the used one.
        assert auth.load_credentials()["refresh_token"] == "r2"

    def test_expired_token_without_refresh_token_is_returned_as_is(
        self, requests_mock, isolated_config
    ):
        auth.save_credentials({"access_token": "a1", "expires_at": time.time() - 1})

        assert auth.get_stored_access_token() == "a1"
        assert not requests_mock.called

    def test_failed_refresh_asks_for_login(self, requests_mock, isolated_config):
        requests_mock.post(
            "https://api.innoactive.io/oauth/token/",
            json={"error": "invalid_grant"},
            status_code=400,
        )
        auth.save_credentials(
            {
                "access_token": "a1",
                "refresh_token": "r1",
                "client_id": "my-client",
                "endpoint": "https://api.innoactive.io",
                "expires_at": time.time() - 1,
            }
        )

        with pytest.raises(Exception, match="auth login"):
            auth.get_stored_access_token()


class TestBearerHeaderFallback:
    def test_env_var_takes_precedence(self, isolated_config, monkeypatch):
        from portal_client import utils

        auth.save_credentials({"access_token": "stored-token"})
        monkeypatch.setenv("PORTAL_BACKEND_ACCESS_TOKEN", "env-token")
        assert utils.get_bearer_authorization_header() == "Bearer env-token"

    def test_falls_back_to_stored_token(self, isolated_config, monkeypatch):
        from portal_client import utils

        monkeypatch.delenv("PORTAL_BACKEND_ACCESS_TOKEN", raising=False)
        auth.save_credentials({"access_token": "stored-token"})
        assert utils.get_bearer_authorization_header() == "Bearer stored-token"

    def test_raises_without_any_token(self, isolated_config, monkeypatch):
        from portal_client import utils

        monkeypatch.delenv("PORTAL_BACKEND_ACCESS_TOKEN", raising=False)
        with pytest.raises(Exception, match="auth login"):
            utils.get_bearer_authorization_header()
