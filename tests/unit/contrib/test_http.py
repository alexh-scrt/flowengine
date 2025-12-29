"""Tests for FlowEngine HTTP component."""

import pytest

from flowengine import FlowContext
from flowengine.contrib.http import HTTPComponent, HTTPX_AVAILABLE


class TestHTTPComponent:
    """Tests for HTTPComponent class."""

    @pytest.fixture
    def component(self) -> HTTPComponent:
        """Create an HTTP component instance."""
        comp = HTTPComponent("fetcher")
        comp.init({
            "base_url": "https://api.example.com",
            "timeout": 30,
        })
        return comp

    @pytest.fixture
    def context(self) -> FlowContext:
        """Create a context for testing."""
        ctx = FlowContext()
        ctx.set("endpoint", "/users/123")
        return ctx

    def test_init_defaults(self) -> None:
        """Test default configuration."""
        comp = HTTPComponent("fetcher")
        comp.init({"base_url": "https://api.example.com"})

        assert comp.base_url == "https://api.example.com"
        assert comp.timeout == 30.0
        assert comp.headers == {}
        assert comp.method == "GET"
        assert comp.endpoint_key == "endpoint"
        assert comp.result_key == "fetcher"

    def test_init_custom_config(self) -> None:
        """Test custom configuration."""
        comp = HTTPComponent("api")
        comp.init({
            "base_url": "https://api.example.com",
            "timeout": 60.0,
            "headers": {"Authorization": "Bearer token123"},
            "method": "POST",
            "endpoint_key": "path",
            "result_key": "response",
        })

        assert comp.base_url == "https://api.example.com"
        assert comp.timeout == 60.0
        assert comp.headers == {"Authorization": "Bearer token123"}
        assert comp.method == "POST"
        assert comp.endpoint_key == "path"
        assert comp.result_key == "response"

    def test_validate_config_valid(self) -> None:
        """Test validation with valid config."""
        comp = HTTPComponent("fetcher")
        comp.init({"base_url": "https://api.example.com"})

        errors = comp.validate_config()
        # May have httpx error if not installed
        if HTTPX_AVAILABLE:
            assert errors == []

    def test_validate_config_missing_base_url(self) -> None:
        """Test validation with missing base_url."""
        comp = HTTPComponent("fetcher")
        comp.init({})

        errors = comp.validate_config()
        assert any("base_url" in e for e in errors)

    def test_validate_config_invalid_method(self) -> None:
        """Test validation with invalid HTTP method."""
        comp = HTTPComponent("fetcher")
        comp.init({
            "base_url": "https://api.example.com",
            "method": "INVALID",
        })

        errors = comp.validate_config()
        assert any("method" in e.lower() for e in errors)

    def test_validate_all_valid_methods(self) -> None:
        """Test all valid HTTP methods."""
        valid_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

        for method in valid_methods:
            comp = HTTPComponent("fetcher")
            comp.init({
                "base_url": "https://api.example.com",
                "method": method,
            })
            errors = comp.validate_config()
            # Only check method-related errors
            method_errors = [e for e in errors if "method" in e.lower()]
            assert method_errors == [], f"Failed for method: {method}"

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_setup_creates_client(
        self, component: HTTPComponent, context: FlowContext
    ) -> None:
        """Test setup creates HTTP client."""
        assert component._client is None
        component.setup(context)
        assert component._client is not None

    @pytest.mark.skipif(not HTTPX_AVAILABLE, reason="httpx not installed")
    def test_teardown_closes_client(
        self, component: HTTPComponent, context: FlowContext
    ) -> None:
        """Test teardown closes HTTP client."""
        component.setup(context)
        assert component._client is not None

        component.teardown(context)
        assert component._client is None

    def test_validate_httpx_not_installed(self) -> None:
        """Test validation error when httpx not installed."""
        if HTTPX_AVAILABLE:
            pytest.skip("httpx is installed")

        comp = HTTPComponent("fetcher")
        comp.init({"base_url": "https://api.example.com"})

        errors = comp.validate_config()
        assert any("httpx" in e.lower() for e in errors)

    def test_process_without_httpx(self, context: FlowContext) -> None:
        """Test process raises error when httpx not installed."""
        if HTTPX_AVAILABLE:
            pytest.skip("httpx is installed")

        comp = HTTPComponent("fetcher")
        comp.init({"base_url": "https://api.example.com"})

        with pytest.raises(RuntimeError, match="httpx"):
            comp.process(context)

    def test_result_key_defaults_to_name(self) -> None:
        """Test result_key defaults to component name."""
        comp = HTTPComponent("my_api_fetcher")
        comp.init({"base_url": "https://api.example.com"})

        assert comp.result_key == "my_api_fetcher"

    def test_result_key_override(self) -> None:
        """Test result_key can be overridden."""
        comp = HTTPComponent("fetcher")
        comp.init({
            "base_url": "https://api.example.com",
            "result_key": "api_response",
        })

        assert comp.result_key == "api_response"
