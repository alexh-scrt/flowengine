# Quick Start

Build and execute your first FlowEngine flow in under 5 minutes.

---

## Step 1: Install FlowEngine

```bash
pip install flowengine
```

---

## Step 2: Create a Component

Components are the building blocks of flows. Create a file `components.py`:

```python
from flowengine import BaseComponent, FlowContext

class FetchDataComponent(BaseComponent):
    """Simulates fetching data from an external source."""

    def process(self, context: FlowContext) -> FlowContext:
        # Simulate fetched data
        context.set("users", [
            {"id": 1, "name": "Alice", "active": True},
            {"id": 2, "name": "Bob", "active": False},
            {"id": 3, "name": "Charlie", "active": True},
        ])
        context.set("fetch_status", "success")
        return context


class FilterActiveComponent(BaseComponent):
    """Filters to only active users."""

    def process(self, context: FlowContext) -> FlowContext:
        users = context.get("users", [])
        active_users = [u for u in users if u.get("active")]
        context.set("active_users", active_users)
        return context


class FormatOutputComponent(BaseComponent):
    """Formats the output for display."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.format_type = config.get("format", "simple")

    def process(self, context: FlowContext) -> FlowContext:
        users = context.get("active_users", [])

        if self.format_type == "detailed":
            output = [f"User {u['id']}: {u['name']}" for u in users]
        else:
            output = [u["name"] for u in users]

        context.set("output", output)
        return context
```

---

## Step 3: Define the Flow

Create a YAML configuration file `flow.yaml`:

```yaml
name: "User Processing Pipeline"
version: "1.0"
description: "Fetch users, filter active ones, and format output"

components:
  - name: fetch
    type: components.FetchDataComponent

  - name: filter
    type: components.FilterActiveComponent

  - name: format
    type: components.FormatOutputComponent
    config:
      format: detailed

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 30

  steps:
    - component: fetch
      description: "Fetch user data"

    - component: filter
      description: "Filter to active users"
      condition: "context.data.fetch_status == 'success'"

    - component: format
      description: "Format the output"
      condition: "context.data.active_users is not None"
```

---

## Step 4: Execute the Flow

Create `main.py`:

```python
from flowengine import ConfigLoader, FlowEngine

# Import your components
from components import (
    FetchDataComponent,
    FilterActiveComponent,
    FormatOutputComponent,
)

# Load the YAML configuration
config = ConfigLoader.load("flow.yaml")

# Create component instances
components = {
    "fetch": FetchDataComponent("fetch"),
    "filter": FilterActiveComponent("filter"),
    "format": FormatOutputComponent("format"),
}

# Create and execute the engine
engine = FlowEngine(config, components)
result = engine.execute()

# Access the results
print("Output:", result.data.output)
print("Duration:", f"{result.metadata.total_duration:.3f}s")
```

Run it:

```bash
python main.py
```

Output:
```
Output: ['User 1: Alice', 'User 3: Charlie']
Duration: 0.002s
```

---

## Step 5: Explore the Metadata

FlowEngine tracks detailed execution metadata:

```python
# Check what ran
print("Steps executed:")
for timing in result.metadata.step_timings:
    print(f"  {timing.component}: {timing.duration:.4f}s")

# Check skipped components
print("Skipped:", result.metadata.skipped_components)

# Check for errors
if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"Error in {error['component']}: {error['message']}")
```

---

## Using Auto-Loading

For simpler setups, let FlowEngine instantiate components automatically:

```python
from flowengine import ConfigLoader, FlowEngine

config = ConfigLoader.load("flow.yaml")

# Auto-instantiate components from type paths
engine = FlowEngine.from_config(config)
result = engine.execute()
```

!!! note
    This requires component classes to be importable from the paths specified in the YAML `type` field.

---

## Quick Start: Graph Flow

Graph flows let you define flows as directed acyclic graphs with conditional branching via output ports.

### Step 1: Create Components

```python
from flowengine import BaseComponent, FlowContext

class FetchComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("data", {"score": 85})
        return context

class ValidatorComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        score = context.get("data", {}).get("score", 0)
        if score >= 70:
            self.set_output_port(context, "pass")
        else:
            self.set_output_port(context, "fail")
        return context

class SuccessComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("result", "approved")
        return context

class FailureComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("result", "rejected")
        return context
```

### Step 2: Define the Graph Flow

```yaml
name: "Validation Pipeline"
version: "1.0"

components:
  - name: fetch
    type: myapp.FetchComponent
  - name: validate
    type: myapp.ValidatorComponent
  - name: on_pass
    type: myapp.SuccessComponent
  - name: on_fail
    type: myapp.FailureComponent

flow:
  type: graph
  settings:
    timeout_seconds: 30
  nodes:
    - id: fetch
      component: fetch
    - id: validate
      component: validate
    - id: success
      component: on_pass
    - id: failure
      component: on_fail
  edges:
    - source: fetch
      target: validate
    - source: validate
      target: success
      port: "pass"
    - source: validate
      target: failure
      port: "fail"
```

### Step 3: Execute

```python
from flowengine import FlowEngine, FlowConfig
from flowengine.config.schema import (
    ComponentConfig, FlowDefinition, FlowSettings,
    GraphNodeConfig, GraphEdgeConfig,
)

components = {
    "fetch": FetchComponent("fetch"),
    "validate": ValidatorComponent("validate"),
    "on_pass": SuccessComponent("on_pass"),
    "on_fail": FailureComponent("on_fail"),
}

config = FlowConfig(
    name="Validation Pipeline",
    version="1.0",
    components=[
        ComponentConfig(name="fetch", type="t.F"),
        ComponentConfig(name="validate", type="t.V"),
        ComponentConfig(name="on_pass", type="t.S"),
        ComponentConfig(name="on_fail", type="t.F"),
    ],
    flow=FlowDefinition(
        type="graph",
        settings=FlowSettings(timeout_seconds=30),
        nodes=[
            GraphNodeConfig(id="fetch", component="fetch"),
            GraphNodeConfig(id="validate", component="validate"),
            GraphNodeConfig(id="success", component="on_pass"),
            GraphNodeConfig(id="failure", component="on_fail"),
        ],
        edges=[
            GraphEdgeConfig(source="fetch", target="validate"),
            GraphEdgeConfig(source="validate", target="success", port="pass"),
            GraphEdgeConfig(source="validate", target="failure", port="fail"),
        ],
    ),
)

engine = FlowEngine(config, components, validate_types=False)
result = engine.execute()

print(result.get("result"))  # "approved"
```

---

## Next Steps

- [Components](user-guide/components.md) - Learn about the component lifecycle
- [Flows](user-guide/flows.md) - Understand sequential, conditional, and graph flows
- [Conditions](user-guide/conditions.md) - Master condition expressions
- [Error Handling](user-guide/error-handling.md) - Handle errors gracefully
