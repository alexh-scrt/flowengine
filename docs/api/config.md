# Configuration Module

Classes for loading and validating flow configurations.

---

## ConfigLoader

Loads and validates YAML flow configurations.

::: flowengine.config.loader.ConfigLoader
    options:
      show_source: false
      members:
        - load
        - loads
        - from_dict

---

## FlowConfig

Complete flow configuration model.

::: flowengine.config.schema.FlowConfig
    options:
      show_source: false
      members:
        - name
        - version
        - description
        - components
        - flow
        - get_component_config
        - settings
        - steps

---

## ComponentConfig

Configuration for a single component.

::: flowengine.config.schema.ComponentConfig
    options:
      show_source: false
      members:
        - name
        - type
        - config

---

## FlowDefinition

Flow structure and execution definition.

::: flowengine.config.schema.FlowDefinition
    options:
      show_source: false
      members:
        - type
        - settings
        - steps

---

## StepConfig

Configuration for a single execution step.

::: flowengine.config.schema.StepConfig
    options:
      show_source: false
      members:
        - component
        - description
        - condition
        - on_error

---

## FlowSettings

Flow execution settings.

::: flowengine.config.schema.FlowSettings
    options:
      show_source: false
      members:
        - fail_fast
        - timeout_seconds
        - timeout_mode
        - require_deadline_check
        - on_condition_error

---

## Usage Examples

### Loading from File

```python
from flowengine import ConfigLoader

config = ConfigLoader.load("flow.yaml")
print(config.name)
print(config.version)
```

### Loading from String

```python
yaml_content = """
name: "Test Flow"
version: "1.0"
components:
  - name: test
    type: myapp.TestComponent
flow:
  steps:
    - component: test
"""

config = ConfigLoader.loads(yaml_content)
```

### Loading from Dictionary

```python
config = ConfigLoader.from_dict({
    "name": "Test Flow",
    "version": "1.0",
    "components": [
        {"name": "test", "type": "myapp.TestComponent"}
    ],
    "flow": {
        "steps": [{"component": "test"}]
    }
})
```

### Accessing Configuration

```python
# Get component config by name
component_config = config.get_component_config("test")
print(component_config.type)

# Access settings
print(config.settings.timeout_seconds)
print(config.settings.fail_fast)

# Iterate steps
for step in config.steps:
    print(f"{step.component}: {step.description}")
```
