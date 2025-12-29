# Contrib Module

Ready-to-use components for common tasks.

---

## LoggingComponent

Logs context state for debugging and monitoring.

::: flowengine.contrib.logging.LoggingComponent
    options:
      show_source: false

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `level` | `str` | `"info"` | Log level: `debug`, `info`, `warning`, `error` |
| `message` | `str` | `"Context state"` | Log message prefix |
| `log_data` | `bool` | `True` | Include context data in log |
| `log_metadata` | `bool` | `False` | Include execution metadata in log |
| `keys` | `list[str]` | `None` | Specific keys to log; `None` = all |

### YAML Configuration

```yaml
components:
  - name: debug_logger
    type: flowengine.contrib.logging.LoggingComponent
    config:
      level: debug
      message: "After processing"
      log_data: true
      log_metadata: true
      keys:
        - user
        - result
```

### Usage Example

```yaml
flow:
  steps:
    - component: fetch_data

    - component: debug_logger
      description: "Log state after fetch"

    - component: process_data

    - component: debug_logger
      description: "Log state after process"
```

---

## HTTPComponent

Makes HTTP requests to external APIs.

!!! note "Installation"
    Requires the `http` extra: `pip install flowengine[http]`

::: flowengine.contrib.http.HTTPComponent
    options:
      show_source: false

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `base_url` | `str` | **required** | Base URL for requests |
| `timeout` | `float` | `30` | Request timeout in seconds |
| `headers` | `dict` | `{}` | HTTP headers to include |
| `method` | `str` | `"GET"` | HTTP method |
| `endpoint_key` | `str` | `"endpoint"` | Context key for endpoint path |
| `result_key` | `str` | component name | Context key for storing result |

### Supported Methods

`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD`, `OPTIONS`

### Response Format

The component stores the response in context:

```python
{
    "status": "success",      # or "error"
    "status_code": 200,       # HTTP status code
    "data": {...},            # Parsed JSON or text
    "headers": {...}          # Response headers
}
```

### YAML Configuration

```yaml
components:
  - name: api_client
    type: flowengine.contrib.http.HTTPComponent
    config:
      base_url: "https://api.example.com"
      timeout: 30
      headers:
        Authorization: "Bearer ${API_TOKEN}"
        Content-Type: "application/json"
      method: GET
```

### Usage Examples

#### Simple GET Request

```yaml
components:
  - name: fetch_users
    type: flowengine.contrib.http.HTTPComponent
    config:
      base_url: "https://api.example.com"
      method: GET

flow:
  steps:
    - component: fetch_users
```

```python
context.set("endpoint", "/users")
result = engine.execute(context)

# Access response
users = result.data.fetch_users.data
status = result.data.fetch_users.status_code
```

#### POST Request with Body

```python
# Set endpoint and body in context
context.set("endpoint", "/users")
context.set("request_body", {"name": "Alice", "email": "alice@example.com"})

# HTTPComponent reads request_body from context
result = engine.execute(context)
```

#### Dynamic Endpoint

```yaml
steps:
  - component: get_user_id
    # Sets context.data.user_id

  - component: fetch_user_details
    # Uses context.data.endpoint set by previous step
```

```python
class GetUserId(BaseComponent):
    def process(self, context):
        user_id = context.get("request_params", {}).get("id")
        context.set("endpoint", f"/users/{user_id}")
        return context
```

#### Error Handling

```yaml
flow:
  settings:
    fail_fast: false

  steps:
    - component: api_call
      on_error: continue

    - component: handle_success
      condition: "context.data.api_call.status == 'success'"

    - component: handle_error
      condition: "context.data.api_call.status == 'error'"
```

---

## Creating Custom Contrib Components

Follow these patterns when creating reusable components:

```python
from flowengine import BaseComponent, FlowContext

class CustomContribComponent(BaseComponent):
    """Custom component for reuse across projects."""

    def init(self, config: dict) -> None:
        super().init(config)
        # Parse configuration with sensible defaults
        self.option = config.get("option", "default")

    def validate_config(self) -> list[str]:
        errors = []
        # Validate required options
        if not self.config.get("required_option"):
            errors.append("required_option is required")
        return errors

    def process(self, context: FlowContext) -> FlowContext:
        # Implement main logic
        result = self.do_something()
        context.set(self.name, result)
        return context
```
