# FlowEngine

**Lightweight YAML-driven state machine for Python**

FlowEngine enables developers to define execution flows declaratively in YAML, build pluggable component systems, and execute conditional branching based on runtime state.

## Features

- **YAML-Driven Configuration** — Define flows in human-readable YAML files
- **Component-Based Architecture** — Build reusable, testable processing units
- **Conditional Execution** — Execute steps based on runtime context state
- **Safe Expression Evaluation** — Condition expressions are validated against an AST allowlist
- **Full Type Hints** — Compatible with mypy strict mode
- **Execution Metadata** — Track timing, errors, and skipped components with step-level detail
- **Cooperative Timeout** — Protect against runaway flows with deadline-based timeouts
- **Component Registry** — Auto-instantiate components from type paths or validate types at runtime
- **Round-Trip Serialization** — Fully serialize and restore context state for replay/debugging
- **Minimal Dependencies** — Only requires `pyyaml` and `pydantic`

## Installation

```bash
pip install flowengine
```

For HTTP component support:

```bash
pip install flowengine[http]
```

For development:

```bash
pip install flowengine[dev]
```

## Quick Start

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

# Load configuration
config = ConfigLoader.load("flow.yaml")

# Create components
components = {"greeter": GreetComponent("greeter")}

# Create engine and execute
engine = FlowEngine(config, components)
context = FlowContext()
context.set("name", "FlowEngine")

result = engine.execute(context)
print(result.data.message)  # "Hello, FlowEngine!"
```

## Core Concepts

### Components

Components are the building blocks of flows. Each component has a lifecycle:

1. `__init__(name)` — Instance creation
2. `init(config)` — One-time configuration (called once)
3. `setup(context)` — Pre-processing (called each run)
4. `process(context)` — Main logic (called each run) **[required]**
5. `teardown(context)` — Cleanup (called each run)

```python
from flowengine import BaseComponent, FlowContext

class DatabaseComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.connection_string = config["connection_string"]
        self._conn = None

    def setup(self, context: FlowContext) -> None:
        self._conn = create_connection(self.connection_string)

    def process(self, context: FlowContext) -> FlowContext:
        data = self._conn.query("SELECT * FROM users")
        context.set("users", data)
        return context

    def teardown(self, context: FlowContext) -> None:
        if self._conn:
            self._conn.close()

    def validate_config(self) -> list[str]:
        errors = []
        if not self.config.get("connection_string"):
            errors.append("connection_string is required")
        return errors
```

### Context

The `FlowContext` carries data through the flow and tracks execution metadata:

```python
from flowengine import FlowContext

context = FlowContext()

# Set values
context.set("user", {"name": "Alice", "age": 30})

# Get values with dot notation
print(context.data.user.name)  # "Alice"

# Check for values
print(context.has("user"))  # True
print(context.get("missing", "default"))  # "default"

# Access metadata
print(context.metadata.flow_id)
print(context.metadata.component_timings)

# Serialize
print(context.to_json())
```

### Flow Configuration

```yaml
name: "My Flow"
version: "1.0"
description: "Optional description"

components:
  - name: component_name
    type: module.path.ComponentClass
    config:
      key: value

flow:
  type: sequential  # or "conditional" for first-match branching

  settings:
    fail_fast: true            # Stop on first error
    timeout_seconds: 300       # Max execution time (cooperative)
    on_condition_error: fail   # fail, skip, or warn

  steps:
    - component: component_name
      description: "What this step does"
      condition: "context.data.ready == True"
      on_error: fail  # fail, skip, or continue
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `fail_fast` | `true` | Stop on first component error |
| `timeout_seconds` | `300` | Maximum flow execution time in seconds |
| `timeout_mode` | `cooperative` | Timeout enforcement: `cooperative`, `hard_async`, `hard_process` |
| `require_deadline_check` | `false` | Require components to call `check_deadline()` in cooperative mode |
| `on_condition_error` | `fail` | How to handle invalid conditions: `fail` (raise exception), `skip` (skip step), `warn` (log and skip) |

## Flow Types

FlowEngine supports two flow execution types:

### Sequential (Default)

Runs **all steps in order**. Each step's condition guards whether that individual step runs.

```yaml
flow:
  type: sequential  # default
  steps:
    - component: fetch_data      # Always runs
    - component: transform_data  # Runs if condition is True
      condition: "context.data.fetch_result.status == 'success'"
    - component: save_data       # Runs if condition is True
      condition: "context.data.transformed is not None"
    - component: notify_error    # Runs if condition is True
      condition: "context.data.fetch_result.status == 'error'"
```

All four steps are evaluated. Multiple steps can execute if their conditions match.

### Conditional (First-Match Branching)

**First-match branching** like a switch/case statement. Stops after the first step whose condition is True.

```yaml
flow:
  type: conditional  # first-match branching
  steps:
    - component: handle_user
      condition: "context.data.request_type == 'user'"
    - component: handle_order
      condition: "context.data.request_type == 'order'"
    - component: handle_admin
      condition: "context.data.request_type == 'admin'"
    - component: handle_unknown  # No condition = default case
```

Only **one step executes**. Once a condition matches, remaining steps are skipped.

| Flow Type | Behavior | Use Case |
|-----------|----------|----------|
| `sequential` | All matching steps run | Data pipelines, multi-step processing |
| `conditional` | First match wins, then stop | Request routing, dispatch, mutually exclusive branches |

## Conditional Step Execution

Steps can have conditions that are evaluated at runtime:

```yaml
steps:
  - component: fetch_data

  - component: process_data
    condition: "context.data.fetch_data.status == 'success'"

  - component: save_data
    condition: "context.data.process_data is not None"

  - component: notify_error
    condition: "context.data.fetch_data.status == 'error'"
```

### Allowed Expressions

Conditions support safe Python expressions:

| Category | Allowed |
|----------|---------|
| **Comparisons** | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| **Logical** | `and`, `or`, `not` |
| **Identity** | `is`, `is not` |
| **Membership** | `in`, `not in` |
| **Attributes** | `context.data.user.name` |
| **Subscripts** | `context.data["key"]` |
| **Constants** | `True`, `False`, `None`, numbers, strings |

**Disallowed for security:**
- Function calls (`len()`, `print()`, etc.)
- Imports
- Lambda expressions
- List comprehensions

## Error Handling

Configure error behavior per step:

```yaml
steps:
  - component: risky_operation
    on_error: continue  # Options: fail, skip, continue

  - component: cleanup
    # Always runs even if previous step failed (with on_error: continue)
```

Use `fail_fast: false` in settings to allow continuing after errors:

```yaml
flow:
  settings:
    fail_fast: false
  steps:
    - component: step1
      on_error: continue  # Log error, continue to next step
    - component: step2
      on_error: skip      # Log error, mark as skipped
    - component: step3
      on_error: fail      # Stop execution (default)
```

Access errors in context:

```python
result = engine.execute(context)

if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"{error['component']}: {error['message']}")
```

## Timeout Handling

Flows can have a maximum execution time:

```yaml
flow:
  settings:
    timeout_seconds: 60  # 60 second limit
    timeout_mode: cooperative  # cooperative (default), hard_async, or hard_process
```

### Timeout Modes

FlowEngine supports three timeout enforcement modes:

| Mode | Enforcement | Use Case |
|------|-------------|----------|
| `cooperative` | Components call `check_deadline()` | Default, safest for complex components |
| `hard_async` | Uses `asyncio.wait_for` | I/O-bound components, async-friendly code |
| `hard_process` | Runs in separate process | CPU-bound components, guaranteed termination |

### Cooperative Mode (Default)

The engine sets a **deadline** before each step and checks between steps. Components cooperate by calling `check_deadline()`:

```python
class LongRunningComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        for item in large_dataset:
            self.check_deadline(context)  # Check periodically
            process_item(item)
        return context
```

**Strict Enforcement:** Enable `require_deadline_check: true` to raise an error when long-running components don't call `check_deadline()`:

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: cooperative
    require_deadline_check: true  # Raise error instead of warning
```

### Hard Async Mode

Uses `asyncio.wait_for` to enforce timeouts. Components run in a thread executor, allowing cancellation:

```yaml
flow:
  settings:
    timeout_seconds: 10
    timeout_mode: hard_async
```

**Guarantees:**
- Timeout is enforced even if component doesn't call `check_deadline()`
- Teardown always runs (in main thread)
- Best for I/O-bound operations

### Hard Process Mode

Runs each step in a separate process with a hard kill on timeout:

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: hard_process
```

**Guarantees:**
- Component is forcibly terminated on timeout
- Teardown always runs in main process
- Context is serialized/deserialized across process boundary
- Best for CPU-bound operations that may hang

**Requirements:**
- Components must be picklable (standard Python classes)
- Context data must be JSON-serializable

### Timeout Guarantees by Mode

| Scenario | Cooperative | Hard Async | Hard Process |
|----------|-------------|------------|--------------|
| Between steps | ✅ Always | ✅ Always | ✅ Always |
| Component calls `check_deadline()` | ✅ Yes | ✅ Yes | ✅ Yes |
| Component blocks without checking | ❌ Runs until returns | ✅ Cancelled | ✅ Killed |
| Teardown runs on timeout | ✅ Yes | ✅ Yes | ✅ Yes |

### Choosing a Timeout Mode

```
┌─────────────────────────────────────────────────────────────┐
│                    Choose Timeout Mode                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Components call check_deadline()?                          │
│    └── YES → Use cooperative (default, safest)              │
│    └── NO  → Components do I/O operations?                  │
│                └── YES → Use hard_async                     │
│                └── NO  → Components are CPU-bound?          │
│                            └── YES → Use hard_process       │
│                            └── NO  → Use cooperative        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Error Handling

```python
from flowengine import FlowTimeoutError, DeadlineCheckError

try:
    result = engine.execute()
except FlowTimeoutError as e:
    print(f"Timed out after {e.elapsed:.2f}s (limit: {e.timeout}s)")
except DeadlineCheckError as e:
    print(f"Component '{e.component}' didn't call check_deadline()")
```

### Best Practices for Timeout Compliance

1. **Cooperative mode:** Call `self.check_deadline(context)` in loops and before I/O
2. **Hard async:** Keep components stateless when possible
3. **Hard process:** Ensure context data is JSON-serializable
4. **All modes:** Implement proper `teardown()` for cleanup

## Component Registry

For YAML-complete flows, you can auto-instantiate components from their type paths:

```python
from flowengine import ConfigLoader, FlowEngine

# Load config and create engine with auto-instantiation
config = ConfigLoader.load("flow.yaml")
engine = FlowEngine.from_config(config)

result = engine.execute()
```

Or use the registry directly:

```python
from flowengine import ComponentRegistry, FlowEngine

registry = ComponentRegistry()
registry.register_class("greeter", GreetComponent)

# Registry is used when creating engine
engine = FlowEngine.from_config(config, registry=registry)
```

Validate that provided components match their declared types:

```python
engine = FlowEngine(config, components)
errors = engine.validate_component_types()
if errors:
    print("Type mismatches:", errors)
```

## Step Timing Details

Execution metadata tracks timing per step, even for repeated components:

```python
result = engine.execute()

# Individual step timings (preserves order)
for timing in result.metadata.step_timings:
    print(f"Step {timing.step_index}: {timing.component} took {timing.duration:.3f}s")

# Aggregated by component (backward-compatible)
for name, total in result.metadata.component_timings.items():
    print(f"{name}: {total:.3f}s total")
```

## Context Serialization

Contexts can be fully serialized and restored:

```python
from flowengine import FlowContext

# After execution
result = engine.execute()

# Serialize to JSON
json_str = result.to_json()

# Later, restore the context
restored = FlowContext.from_json(json_str)

# All data preserved
print(restored.get("key"))
print(restored.metadata.flow_id)
print(restored.metadata.step_timings)
```

## Contrib Components

### LoggingComponent

Logs context state for debugging:

```yaml
- name: debug
  type: flowengine.contrib.logging.LoggingComponent
  config:
    level: debug  # debug, info, warning, error
    message: "Current state"
    log_data: true
    log_metadata: false
    keys:  # Optional: only log specific keys
      - user
      - result
```

### HTTPComponent

Makes HTTP requests (requires `pip install flowengine[http]`):

```yaml
- name: api
  type: flowengine.contrib.http.HTTPComponent
  config:
    base_url: "https://api.example.com"
    timeout: 30
    headers:
      Authorization: "Bearer token"
    method: GET  # GET, POST, PUT, PATCH, DELETE
```

Usage:

```python
context.set("endpoint", "/users/123")
result = engine.execute(context)
print(result.data.api.data)  # Response JSON
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `BaseComponent` | Abstract base class for components |
| `FlowContext` | Context passed through all components |
| `DotDict` | Dictionary with attribute-style access |
| `ExecutionMetadata` | Tracks timing, errors, and execution state |
| `StepTiming` | Timing info for a single step execution |
| `FlowEngine` | Orchestrates flow execution |

### Configuration Classes

| Class | Description |
|-------|-------------|
| `ConfigLoader` | Loads YAML configurations |
| `FlowConfig` | Complete flow configuration model |
| `ComponentConfig` | Component configuration model |
| `StepConfig` | Step configuration model |
| `FlowSettings` | Execution settings model |
| `ComponentRegistry` | Registry for dynamic component loading |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `FlowEngineError` | Base exception for all errors |
| `ConfigurationError` | Invalid configuration |
| `FlowExecutionError` | Runtime execution error |
| `FlowTimeoutError` | Flow exceeded timeout_seconds |
| `DeadlineCheckError` | Component didn't call check_deadline() (with require_deadline_check=True) |
| `ComponentError` | Component processing error |
| `ConditionEvaluationError` | Invalid/unsafe condition |

## Examples

See the `examples/` directory for complete examples:

- `simple_flow.py` — Basic flow execution
- `conditional_flow.py` — Sequential flow with conditional steps
- `routing_flow.py` — Conditional flow with first-match branching
- `timeout_modes.py` — Timeout enforcement modes (cooperative, hard_async, hard_process)
- `custom_components.py` — Advanced component patterns

Run examples:

```bash
cd examples
python simple_flow.py
python conditional_flow.py
python routing_flow.py
python timeout_modes.py
python custom_components.py
```

## Development

### Setup

```bash
git clone https://github.com/yourorg/flowengine.git
cd flowengine
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v --cov=flowengine
```

### Type Checking

```bash
mypy src/flowengine
```

### Linting

```bash
ruff check src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request
