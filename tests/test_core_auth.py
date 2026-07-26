"""Tests for Authentication Layer — providers, credentials, injector, manager."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.auth.credentials import CredentialStore
from core.auth.injector import apply_auth_to_request_kwargs, create_auth_for_provider, inject_into_client
from core.auth.manager import AuthManager, AuthTarget, get_auth_manager
from core.auth.provider import (
    APIKeyHeaderProvider,
    APIKeyQueryProvider,
    AuthConfig,
    AuthType,
    BasicAuthProvider,
    BearerTokenProvider,
    CookieProvider,
    JWTProvider,
    get_provider,
    list_providers,
)

# ── Provider Tests ──────────────────────────────────────────────


class TestProviders:
    def test_bearer_token_headers(self):
        config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={"token": "my-token"})
        provider = BearerTokenProvider()
        headers = provider.get_headers(config)
        assert headers["Authorization"] == "Bearer my-token"

    def test_jwt_headers(self):
        config = AuthConfig(auth_type=AuthType.JWT, params={"token": "jwt.val.ue"})
        provider = JWTProvider()
        headers = provider.get_headers(config)
        assert headers["Authorization"] == "Bearer jwt.val.ue"

    def test_cookie_headers(self):
        config = AuthConfig(auth_type=AuthType.COOKIE, params={"cookie": "session=abc; user=me"})
        provider = CookieProvider()
        headers = provider.get_headers(config)
        assert headers["Cookie"] == "session=abc; user=me"

    def test_cookie_get_cookies(self):
        config = AuthConfig(auth_type=AuthType.COOKIE, params={"cookie": "session=abc; user=me"})
        provider = CookieProvider()
        cookies = provider.get_cookies(config)
        assert cookies["session"] == "abc"
        assert cookies["user"] == "me"

    def test_basic_auth_headers(self):
        config = AuthConfig(auth_type=AuthType.BASIC_AUTH, params={"username": "admin", "password": "secret"})
        provider = BasicAuthProvider()
        headers = provider.get_headers(config)
        import base64

        expected = base64.b64encode(b"admin:secret").decode()
        assert headers["Authorization"] == f"Basic {expected}"

    def test_api_key_header_headers(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={"key": "sk-123", "header_name": "X-API-Key"})
        provider = APIKeyHeaderProvider()
        headers = provider.get_headers(config)
        assert headers["X-API-Key"] == "sk-123"

    def test_api_key_header_default_name(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={"key": "sk-456"})
        config.params.setdefault("header_name", "X-API-Key")
        provider = APIKeyHeaderProvider()
        headers = provider.get_headers(config)
        assert headers["X-API-Key"] == "sk-456"

    def test_api_key_query_params(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_QUERY, params={"key": "qkey", "param_name": "apikey"})
        provider = APIKeyQueryProvider()
        params = provider.get_query_params(config)
        assert params["apikey"] == "qkey"

    def test_get_provider(self):
        assert get_provider(AuthType.BEARER_TOKEN) is not None
        assert get_provider(AuthType.JWT) is not None
        assert get_provider(AuthType.COOKIE) is not None
        assert get_provider(AuthType.BASIC_AUTH) is not None
        assert get_provider(AuthType.API_KEY_HEADER) is not None
        assert get_provider(AuthType.API_KEY_QUERY) is not None

    def test_supports(self):
        provider = BearerTokenProvider()
        assert provider.supports(AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={}))
        assert not provider.supports(AuthConfig(auth_type=AuthType.JWT, params={}))

    def test_list_providers(self):
        providers = list_providers()
        assert AuthType.BEARER_TOKEN in providers
        assert AuthType.API_KEY_QUERY in providers
        assert len(providers) >= 6


class TestAuthConfigValidation:
    def test_valid_bearer_token(self):
        config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={"token": "x"})
        assert config.validate() == []

    def test_invalid_bearer_token(self):
        config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={})
        errors = config.validate()
        assert len(errors) == 1
        assert "token" in errors[0]

    def test_valid_jwt(self):
        config = AuthConfig(auth_type=AuthType.JWT, params={"token": "x"})
        assert config.validate() == []

    def test_invalid_jwt(self):
        config = AuthConfig(auth_type=AuthType.JWT, params={})
        errors = config.validate()
        assert len(errors) == 1

    def test_valid_cookie(self):
        config = AuthConfig(auth_type=AuthType.COOKIE, params={"cookie": "a=b"})
        assert config.validate() == []

    def test_valid_basic_auth(self):
        config = AuthConfig(auth_type=AuthType.BASIC_AUTH, params={"username": "u", "password": "p"})
        assert config.validate() == []

    def test_invalid_basic_auth(self):
        config = AuthConfig(auth_type=AuthType.BASIC_AUTH, params={"username": "u"})
        errors = config.validate()
        assert len(errors) == 1

    def test_valid_api_key_header(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={"key": "k"})
        assert config.validate() == []

    def test_invalid_api_key_header(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={})
        errors = config.validate()
        assert len(errors) == 1


# ── Injector Tests ────────────────────────────────────────────────


class TestInjector:
    def test_create_auth_for_provider_bearer(self):
        config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={"token": "t"})
        result = create_auth_for_provider(config)
        assert result["headers"]["Authorization"] == "Bearer t"
        assert result["auth"] is None

    def test_create_auth_for_provider_basic(self):
        config = AuthConfig(auth_type=AuthType.BASIC_AUTH, params={"username": "u", "password": "p"})
        result = create_auth_for_provider(config)
        assert result["headers"]["Authorization"].startswith("Basic ")
        assert result["auth"] is not None

    def test_create_auth_for_provider_unknown(self):
        result = create_auth_for_provider(AuthConfig(auth_type="unknown", params={}))  # type: ignore
        assert result == {}

    def test_apply_auth_to_request_kwargs(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={"key": "k", "header_name": "X-Key"})
        kwargs = {"headers": {"Content-Type": "application/json"}, "params": {}}
        result = apply_auth_to_request_kwargs(kwargs, config)
        assert result["headers"]["X-Key"] == "k"
        assert result["headers"]["Content-Type"] == "application/json"

    def test_apply_auth_to_request_kwargs_no_headers(self):
        config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={"token": "t"})
        kwargs: dict = {}
        result = apply_auth_to_request_kwargs(kwargs, config)
        assert result["headers"]["Authorization"] == "Bearer t"

    def test_apply_auth_query_params(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_QUERY, params={"key": "qk", "param_name": "key"})
        kwargs = {"headers": {}, "params": {"page": "1"}}
        result = apply_auth_to_request_kwargs(kwargs, config)
        assert result["params"]["key"] == "qk"
        assert result["params"]["page"] == "1"

    def test_inject_into_client(self):
        config = AuthConfig(auth_type=AuthType.API_KEY_HEADER, params={"key": "sk", "header_name": "X-API-Key"})
        client = MagicMock()
        client.headers = {}
        client.auth = None
        result = inject_into_client(client, config)
        assert result.headers["X-API-Key"] == "sk"


# ── CredentialStore Tests ──────────────────────────────────────────


class TestCredentialStore:
    def test_store_and_load(self):
        store = CredentialStore()
        store._vault = MagicMock()
        store._vault.get_credentials.return_value = {
            "token": '{"provider": "test", "auth_type": "bearer_token", "params": {"token": "s3cret"}, "label": "test"}'
        }

        entry = store.load("test")
        assert entry is not None
        assert entry.auth_type == AuthType.BEARER_TOKEN
        assert entry.params["token"] == "s3cret"

    def test_load_missing(self):
        store = CredentialStore()
        store._vault = MagicMock()
        store._vault.get_credentials.return_value = {}

        entry = store.load("nonexistent")
        assert entry is None

    def test_delete(self):
        store = CredentialStore()
        store._vault = MagicMock()
        result = store.delete("test")
        assert result is True


# ── AuthManager Tests ──────────────────────────────────────────────


class TestAuthManager:
    def setup_method(self):
        self.manager = AuthManager()
        self.config = AuthConfig(auth_type=AuthType.BEARER_TOKEN, params={"token": "test-token"})

    def test_register_and_get(self):
        target = AuthTarget(target_id=1, target_name="test", auth_config=self.config)
        self.manager.register_target(target)
        retrieved = self.manager.get_auth(1)
        assert retrieved is not None
        assert retrieved.params["token"] == "test-token"

    def test_get_nonexistent(self):
        assert self.manager.get_auth(999) is None

    def test_unregister(self):
        target = AuthTarget(target_id=1, target_name="test", auth_config=self.config)
        self.manager.register_target(target)
        assert self.manager.unregister_target(1) is True
        assert self.manager.get_auth(1) is None

    def test_unregister_nonexistent(self):
        assert self.manager.unregister_target(999) is False

    def test_apply_auth(self):
        target = AuthTarget(target_id=1, target_name="test", auth_config=self.config)
        self.manager.register_target(target)
        kwargs = self.manager.apply_auth(1, {"headers": {}, "params": {}})
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"

    def test_apply_auth_no_config(self):
        kwargs = self.manager.apply_auth(999, {"headers": {}, "params": {}})
        assert kwargs == {"headers": {}, "params": {}}

    def test_enable_disable(self):
        target = AuthTarget(target_id=1, target_name="test", auth_config=self.config)
        self.manager.register_target(target)
        assert self.manager.disable_target(1) is True
        assert self.manager.get_auth(1) is None
        assert self.manager.enable_target(1) is True
        assert self.manager.get_auth(1) is not None

    def test_enable_disable_nonexistent(self):
        assert self.manager.enable_target(999) is False
        assert self.manager.disable_target(999) is False

    def test_list_targets(self):
        t1 = AuthTarget(target_id=1, target_name="t1", auth_config=self.config)
        t2 = AuthTarget(target_id=2, target_name="t2", auth_config=self.config)
        self.manager.register_target(t1)
        self.manager.register_target(t2)
        targets = self.manager.list_targets()
        assert len(targets) == 2
        assert {t.target_id for t in targets} == {1, 2}

    def test_test_auth_no_config(self):
        assert self.manager.test_auth(999) is False

    def test_get_auth_manager_singleton(self):
        m1 = get_auth_manager()
        m2 = get_auth_manager()
        assert m1 is m2


# ── Auth Target Tests ──────────────────────────────────────────────


class TestAuthTarget:
    def test_create(self):
        config = AuthConfig(auth_type=AuthType.COOKIE, params={"cookie": "a=b"})
        target = AuthTarget(target_id=42, target_name="example", auth_config=config)
        assert target.target_id == 42
        assert target.target_name == "example"
        assert target.auth_config.auth_type == AuthType.COOKIE
        assert target.enabled is True
