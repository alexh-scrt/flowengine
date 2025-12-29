"""HTTP component for FlowEngine.

Provides a component that makes HTTP requests using httpx.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from flowengine.core.component import BaseComponent

if TYPE_CHECKING:
    from flowengine.core.context import FlowContext

try:
    import httpx

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None  # type: ignore[assignment]


class HTTPComponent(BaseComponent):
    """Component that makes HTTP requests.

    Fetches data from HTTP endpoints and stores responses in context.
    Requires the httpx package: pip install flowengine[http]

    Config:
        base_url: Base URL for requests (required)
        timeout: Request timeout in seconds. Default: 30
        headers: Optional headers dictionary. Default: {}
        method: HTTP method. Default: GET
        endpoint_key: Context key for endpoint path. Default: "endpoint"
        result_key: Context key for storing result. Default: component name

    Example YAML:
        ```yaml
        - name: api_fetch
          type: flowengine.contrib.http.HTTPComponent
          config:
            base_url: "https://api.example.com"
            timeout: 30
            headers:
              Authorization: "Bearer ${API_TOKEN}"
        ```

    Example usage:
        ```python
        fetcher = HTTPComponent("api_fetch")
        fetcher.init({
            "base_url": "https://api.example.com",
            "timeout": 30
        })

        context = FlowContext()
        context.set("endpoint", "/users/123")
        context = fetcher.process(context)

        print(context.data.api_fetch.status_code)  # 200
        print(context.data.api_fetch.data)  # Response JSON
        ```
    """

    def init(self, config: dict[str, Any]) -> None:
        """Initialize with HTTP configuration.

        Args:
            config: Configuration dictionary
        """
        super().init(config)
        self.base_url: str = config.get("base_url", "")
        self.timeout: float = config.get("timeout", 30.0)
        self.headers: dict[str, str] = config.get("headers", {})
        self.method: str = config.get("method", "GET").upper()
        self.endpoint_key: str = config.get("endpoint_key", "endpoint")
        self.result_key: str = config.get("result_key", self.name)

        self._client: Any = None  # httpx.Client

    def validate_config(self) -> list[str]:
        """Validate HTTP configuration.

        Returns:
            List of validation errors
        """
        errors = super().validate_config()

        if not HTTPX_AVAILABLE:
            errors.append(
                "httpx is not installed. "
                "Install with: pip install flowengine[http]"
            )

        if not self.base_url:
            errors.append("base_url is required")

        valid_methods = ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS")
        if self.method not in valid_methods:
            errors.append(f"Invalid method: {self.method}. Must be one of {valid_methods}")

        return errors

    def setup(self, context: FlowContext) -> None:
        """Create HTTP client for this run.

        Args:
            context: Current flow context
        """
        if not HTTPX_AVAILABLE:
            return

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout,
            headers=self.headers,
        )

    def process(self, context: FlowContext) -> FlowContext:
        """Fetch data and store in context.

        Args:
            context: Current flow context

        Returns:
            Updated flow context with response data

        Raises:
            RuntimeError: If httpx is not available
            httpx.HTTPError: If request fails
        """
        if not HTTPX_AVAILABLE:
            raise RuntimeError(
                "httpx is not installed. "
                "Install with: pip install flowengine[http]"
            )

        endpoint = context.get(self.endpoint_key, "/")

        # Make request based on method
        if self.method == "GET":
            response = self._client.get(endpoint)
        elif self.method == "POST":
            body = context.get("request_body", {})
            response = self._client.post(endpoint, json=body)
        elif self.method == "PUT":
            body = context.get("request_body", {})
            response = self._client.put(endpoint, json=body)
        elif self.method == "PATCH":
            body = context.get("request_body", {})
            response = self._client.patch(endpoint, json=body)
        elif self.method == "DELETE":
            response = self._client.delete(endpoint)
        else:
            response = self._client.request(self.method, endpoint)

        response.raise_for_status()

        # Store result in context
        try:
            data = response.json()
        except Exception:
            data = response.text

        context.set(
            self.result_key,
            {
                "status": "success",
                "status_code": response.status_code,
                "data": data,
                "headers": dict(response.headers),
            },
        )

        return context

    def teardown(self, context: FlowContext) -> None:
        """Close HTTP client.

        Args:
            context: Current flow context
        """
        if self._client:
            self._client.close()
            self._client = None
