# Registry Module

Dynamic component loading and registration.

---

## ComponentRegistry

Registry for managing and instantiating components.

::: flowengine.config.registry.ComponentRegistry
    options:
      show_source: false
      members:
        - __init__
        - register_class
        - get_class
        - create
        - create_from_path
        - list_registered

---

## Functions

### load_component_class

Load a component class from its fully qualified path.

::: flowengine.config.registry.load_component_class
    options:
      show_source: false

### validate_component_type

Validate that a component instance matches its declared type.

::: flowengine.config.registry.validate_component_type
    options:
      show_source: false

---

## Usage Examples

### Basic Registry Usage

```python
from flowengine import ComponentRegistry, BaseComponent

class MyComponent(BaseComponent):
    def process(self, context):
        return context

# Create registry and register class
registry = ComponentRegistry()
registry.register_class("my_component", MyComponent)

# Create instance
component = registry.create("my_component", "instance_name")
```

### Auto-Loading from Type Path

```python
from flowengine import ComponentRegistry

registry = ComponentRegistry()

# Load from fully qualified path
component = registry.create_from_path(
    "myapp.components.ProcessorComponent",
    "processor"
)
```

### Using with FlowEngine

```python
from flowengine import ConfigLoader, FlowEngine, ComponentRegistry

config = ConfigLoader.load("flow.yaml")

# Option 1: Auto-instantiate all components
engine = FlowEngine.from_config(config)

# Option 2: Use custom registry
registry = ComponentRegistry()
registry.register_class("processor", CustomProcessor)

engine = FlowEngine.from_config(config, registry=registry)
```

### Type Validation

```python
from flowengine import load_component_class, validate_component_type

# Load class from path
component_class = load_component_class("myapp.MyComponent")
component = component_class("my_instance")

# Validate type matches
error = validate_component_type(
    component,
    "myapp.MyComponent"
)

if error:
    print(f"Type mismatch: {error}")
```

### Listing Registered Components

```python
registry = ComponentRegistry()
registry.register_class("fetcher", FetchComponent)
registry.register_class("processor", ProcessComponent)
registry.register_class("saver", SaveComponent)

registered = registry.list_registered()
print(registered)  # ["fetcher", "processor", "saver"]
```
