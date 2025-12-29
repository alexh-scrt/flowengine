# FlowEngine

**Lightweight YAML-driven state machine for Python**

FlowEngine enables developers to define execution flows declaratively in YAML, build pluggable component systems, and execute conditional branching based on runtime state.

---

## Why FlowEngine?

- **Declarative Configuration**: Define complex workflows in human-readable YAML
- **Separation of Concerns**: Business logic lives in components, flow logic lives in YAML
- **Runtime Flexibility**: Conditions evaluated at runtime allow dynamic behavior
- **Observability**: Built-in timing, error tracking, and execution metadata
- **Type Safety**: Full type hints compatible with mypy strict mode

---

## Key Features

<div class="grid cards" markdown>

-   :material-file-document-edit:{ .lg .middle } **YAML-Driven Configuration**

    ---

    Define flows in human-readable YAML files with full schema validation

-   :material-puzzle:{ .lg .middle } **Component-Based Architecture**

    ---

    Build reusable, testable processing units with clear lifecycle hooks

-   :material-source-branch:{ .lg .middle } **Conditional Execution**

    ---

    Execute steps based on runtime context with safe expression evaluation

-   :material-timer:{ .lg .middle } **Timeout Protection**

    ---

    Three timeout modes: cooperative, hard async, and hard process isolation

-   :material-chart-timeline:{ .lg .middle } **Execution Metadata**

    ---

    Track timing, errors, and skipped components with step-level detail

-   :material-serialize:{ .lg .middle } **Round-Trip Serialization**

    ---

    Fully serialize and restore context state for replay and debugging

</div>

---

## Quick Example

### 1. Define a Component

```python
from flowengine import BaseComponent, FlowContext

class GreetComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.greeting = config.get("greeting", "Hello")

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("name", "World")
        context.set("message", f"{self.greeting}, {name}!")
        return context
```

### 2. Create a Flow Configuration

```yaml
# flow.yaml
name: "Greeting Flow"
version: "1.0"

components:
  - name: greeter
    type: myapp.GreetComponent
    config:
      greeting: "Hello"

flow:
  steps:
    - component: greeter
      description: "Generate greeting"
```

### 3. Execute the Flow

```python
from flowengine import ConfigLoader, FlowEngine, FlowContext

config = ConfigLoader.load("flow.yaml")
components = {"greeter": GreetComponent("greeter")}
engine = FlowEngine(config, components)

context = FlowContext()
context.set("name", "FlowEngine")

result = engine.execute(context)
print(result.data.message)  # "Hello, FlowEngine!"
```

---

## Flow Types

FlowEngine supports two execution modes:

| Flow Type | Behavior | Use Case |
|-----------|----------|----------|
| `sequential` | All matching steps run in order | Data pipelines, multi-step processing |
| `conditional` | First matching condition wins | Request routing, dispatch, switch/case |

---

## Getting Started

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **[Installation](installation.md)**

    ---

    Install FlowEngine and optional dependencies

-   :material-rocket-launch:{ .lg .middle } **[Quick Start](quickstart.md)**

    ---

    Build your first flow in 5 minutes

-   :material-book-open-variant:{ .lg .middle } **[User Guide](user-guide/components.md)**

    ---

    Deep dive into components, flows, and patterns

-   :material-api:{ .lg .middle } **[API Reference](api/index.md)**

    ---

    Complete API documentation

</div>

---

## Requirements

- Python 3.11+
- pyyaml >= 6.0
- pydantic >= 2.0

---

## License

FlowEngine is released under the [MIT License](https://github.com/yourorg/flowengine/blob/main/LICENSE).
