# Installation

## Requirements

- Python 3.11 or higher
- pip or poetry package manager

---

## Basic Installation

Install FlowEngine from PyPI:

```bash
pip install flowengine
```

This installs the core package with minimal dependencies:

- `pyyaml` - YAML configuration parsing
- `pydantic` - Configuration validation

---

## Optional Dependencies

### HTTP Components

For the built-in `HTTPComponent` that makes HTTP requests:

```bash
pip install flowengine[http]
```

This adds:

- `httpx` - Modern HTTP client

### Development

For development and testing:

```bash
pip install flowengine[dev]
```

This adds:

- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pytest-asyncio` - Async test support
- `mypy` - Static type checking
- `ruff` - Fast Python linter
- `types-PyYAML` - Type stubs for PyYAML

### All Optional Dependencies

Install everything:

```bash
pip install flowengine[http,dev]
```

---

## Using Poetry

If you prefer Poetry:

```bash
poetry add flowengine
```

With optional dependencies:

```bash
poetry add flowengine -E http
```

---

## Development Setup

Clone the repository and install in development mode:

```bash
git clone https://github.com/yourorg/flowengine.git
cd flowengine
pip install -e ".[dev]"
```

Verify the installation:

```bash
python -c "import flowengine; print(flowengine.__version__)"
```

---

## Verifying Installation

Test that FlowEngine is working:

```python
from flowengine import (
    BaseComponent,
    FlowContext,
    FlowEngine,
    ConfigLoader,
)

# Create a simple component
class HelloComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("greeting", "Hello, FlowEngine!")
        return context

# Create a minimal config
config = ConfigLoader.from_dict({
    "name": "Test Flow",
    "version": "1.0",
    "components": [
        {"name": "hello", "type": "test.HelloComponent"}
    ],
    "flow": {
        "steps": [{"component": "hello"}]
    }
})

# Run the flow
engine = FlowEngine(config, {"hello": HelloComponent("hello")})
result = engine.execute()
print(result.data.greeting)  # "Hello, FlowEngine!"
```

---

## Next Steps

- [Quick Start](quickstart.md) - Build your first flow
- [Components](user-guide/components.md) - Learn about component development
- [API Reference](api/index.md) - Explore the API
