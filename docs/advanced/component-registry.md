# Component Registry

The ComponentRegistry enables dynamic component loading, making flows fully YAML-driven without hardcoding component instantiation.

---

## Overview

Instead of manually creating components:

```python
# Manual instantiation
components = {
    "fetch": FetchComponent("fetch"),
    "process": ProcessComponent("process"),
    "save": SaveComponent("save"),
}
engine = FlowEngine(config, components)
```

Use the registry for automatic instantiation:

```python
# Auto-instantiation from YAML type paths
engine = FlowEngine.from_config(config)
```

---

## Basic Usage

### Auto-Loading from Config

The simplest approach - let FlowEngine load components from their type paths:

```python
from flowengine import ConfigLoader, FlowEngine

config = ConfigLoader.load("flow.yaml")
engine = FlowEngine.from_config(config)
result = engine.execute()
```

YAML configuration:

```yaml
components:
  - name: fetch
    type: myapp.components.FetchComponent
    config:
      source: "api"

  - name: process
    type: myapp.components.ProcessComponent

  - name: save
    type: myapp.components.SaveComponent
    config:
      destination: "database"
```

The registry:

1. Imports each module (`myapp.components`)
2. Gets the class (`FetchComponent`)
3. Instantiates with the name (`FetchComponent("fetch")`)
4. Calls `init(config)` with the config dict

---

## Custom Registry

For more control, create a custom registry:

```python
from flowengine import ComponentRegistry, FlowEngine, ConfigLoader

# Create registry
registry = ComponentRegistry()

# Register classes explicitly
registry.register_class("fetcher", FetchComponent)
registry.register_class("processor", ProcessComponent)
registry.register_class("saver", SaveComponent)

# Load config and create engine
config = ConfigLoader.load("flow.yaml")
engine = FlowEngine.from_config(config, registry=registry)
```

### When to Use Custom Registry

- **Testing**: Register mock components
- **Plugins**: Register dynamically discovered components
- **Aliasing**: Use short names instead of full paths
- **Validation**: Pre-validate component classes

---

## Registry Operations

### Register a Class

```python
registry = ComponentRegistry()
registry.register_class("my_component", MyComponent)
```

### Get a Registered Class

```python
component_class = registry.get_class("my_component")
if component_class:
    instance = component_class("instance_name")
```

### Create from Registered Name

```python
# Create instance using registered name
component = registry.create("my_component", "instance_name")
```

### Create from Type Path

```python
# Create instance from fully qualified path
component = registry.create_from_path(
    "myapp.components.MyComponent",
    "instance_name"
)
```

### List Registered Names

```python
names = registry.list_registered()
print(names)  # ["fetcher", "processor", "saver"]
```

---

## Type Validation

FlowEngine can validate that component instances match their declared types:

### At Engine Creation

```python
# validate_types=True by default
engine = FlowEngine(config, components, validate_types=True)
```

### Manual Validation

```python
from flowengine import validate_component_type

# Returns None if valid, error message if not
error = validate_component_type(
    component=my_component,
    expected_type_path="myapp.MyComponent"
)

if error:
    print(f"Type mismatch: {error}")
```

### Engine-Level Validation

```python
engine = FlowEngine(config, components)
errors = engine.validate_component_types()

if errors:
    for error in errors:
        print(error)
```

---

## Dynamic Loading

### Load a Component Class

```python
from flowengine import load_component_class

# Load class from fully qualified path
component_class = load_component_class("myapp.components.MyComponent")

# Create instance
component = component_class("my_instance")
component.init({"setting": "value"})
```

### Error Handling

```python
from flowengine import load_component_class, ConfigurationError

try:
    component_class = load_component_class("invalid.path.Component")
except ConfigurationError as e:
    print(f"Failed to load: {e.message}")
```

---

## Plugin Architecture

Use the registry to build a plugin system:

```python
import importlib
import pkgutil
from flowengine import ComponentRegistry, BaseComponent

def discover_plugins(package_name: str) -> ComponentRegistry:
    """Discover all component plugins in a package."""
    registry = ComponentRegistry()

    # Import the package
    package = importlib.import_module(package_name)

    # Iterate through submodules
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        # Find all BaseComponent subclasses
        for name, obj in vars(module).items():
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseComponent)
                and obj is not BaseComponent
            ):
                registry.register_class(name.lower(), obj)

    return registry

# Usage
registry = discover_plugins("myapp.plugins")
engine = FlowEngine.from_config(config, registry=registry)
```

---

## Testing with Registry

### Mock Components

```python
import pytest
from flowengine import ComponentRegistry, FlowEngine, ConfigLoader

class MockFetchComponent(BaseComponent):
    def process(self, context):
        context.set("data", {"mocked": True})
        return context

@pytest.fixture
def test_registry():
    registry = ComponentRegistry()
    registry.register_class("fetch", MockFetchComponent)
    return registry

def test_flow_with_mock(test_registry):
    config = ConfigLoader.load("flow.yaml")
    engine = FlowEngine.from_config(config, registry=test_registry)
    result = engine.execute()
    assert result.data.data["mocked"] is True
```

### Partial Mocking

```python
def test_partial_mock():
    # Use real components except for external API calls
    registry = ComponentRegistry()
    registry.register_class("api_client", MockAPIClient)
    # Other components loaded from type paths

    config = ConfigLoader.load("flow.yaml")
    engine = FlowEngine.from_config(config, registry=registry)
```

---

## Best Practices

1. **Use type paths in production**: Full paths in YAML enable automatic loading
2. **Use registry in tests**: Register mocks for isolated testing
3. **Validate types**: Enable `validate_types=True` to catch mismatches
4. **Organize components**: Use clear module paths (`myapp.components.etl`)
5. **Document type paths**: Include type path in component docstrings

---

## Next Steps

- [Serialization](serialization.md) - Context serialization for debugging
- [Architecture](architecture.md) - Internal design
- [API Reference](../api/registry.md) - Full registry API
