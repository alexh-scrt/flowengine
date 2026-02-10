# Components

Components are the building blocks of FlowEngine. Each component encapsulates a unit of business logic that can be configured, tested, and reused across different flows.

---

## Component Lifecycle

Every component follows a defined lifecycle with five methods:

```
┌─────────────────────────────────────────────────────────┐
│                    Component Lifecycle                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. __init__(name)     → Instance creation              │
│          ↓                                              │
│  2. init(config)       → One-time configuration         │
│          ↓                                              │
│  ┌──────────────────── Per Execution ──────────────────┐│
│  │ 3. setup(context)   → Pre-processing                ││
│  │         ↓                                           ││
│  │ 4. process(context) → Main logic [REQUIRED]         ││
│  │         ↓                                           ││
│  │ 5. teardown(context)→ Cleanup (always runs)         ││
│  └─────────────────────────────────────────────────────┘│
│                                                         │
└─────────────────────────────────────────────────────────┘
```

| Method | Called | Purpose |
|--------|--------|---------|
| `__init__(name)` | Once | Instance creation with unique name |
| `init(config)` | Once | Process configuration dictionary |
| `setup(context)` | Each execution | Pre-processing setup |
| `process(context)` | Each execution | **Main logic (required)** |
| `teardown(context)` | Each execution | Cleanup, always runs even on error |

---

## Creating a Component

### Basic Component

```python
from flowengine import BaseComponent, FlowContext

class SimpleComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("result", "Hello from SimpleComponent!")
        return context
```

### Configurable Component

```python
class ConfigurableComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)  # Always call super().init()
        self.multiplier = config.get("multiplier", 1)
        self.prefix = config.get("prefix", "")

    def process(self, context: FlowContext) -> FlowContext:
        value = context.get("input_value", 0)
        result = value * self.multiplier
        context.set("output", f"{self.prefix}{result}")
        return context
```

YAML configuration:

```yaml
components:
  - name: calculator
    type: myapp.ConfigurableComponent
    config:
      multiplier: 10
      prefix: "Result: "
```

---

## Lifecycle Methods in Detail

### init(config)

Called once when the engine initializes. Use for:

- Parsing configuration options
- Initializing instance attributes
- Validating required configuration

```python
def init(self, config: dict) -> None:
    super().init(config)  # Required!

    # Parse configuration
    self.api_key = config.get("api_key")
    self.timeout = config.get("timeout", 30)
    self.retries = config.get("retries", 3)

    # Initialize resources (not connections - do that in setup)
    self._client = None
```

### setup(context)

Called before each `process()`. Use for:

- Opening connections
- Acquiring resources
- Reading initial context state

```python
def setup(self, context: FlowContext) -> None:
    # Open database connection
    self._conn = DatabaseConnection(self.connection_string)

    # Read any required context values
    self._batch_id = context.get("batch_id")
```

### process(context)

The main processing logic. **This is the only required method.**

```python
def process(self, context: FlowContext) -> FlowContext:
    # Read input
    data = context.get("input_data")

    # Process
    result = self.transform(data)

    # Write output
    context.set("output_data", result)

    return context  # Always return context
```

### teardown(context)

Called after `process()` completes, **even if it raised an exception**. Use for:

- Closing connections
- Releasing resources
- Final cleanup

```python
def teardown(self, context: FlowContext) -> None:
    if self._conn:
        self._conn.close()
        self._conn = None
```

---

## Configuration Validation

Override `validate_config()` to check required settings:

```python
class DatabaseComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.connection_string = config.get("connection_string")
        self.table_name = config.get("table_name")

    def validate_config(self) -> list[str]:
        errors = []

        if not self.connection_string:
            errors.append("connection_string is required")

        if not self.table_name:
            errors.append("table_name is required")

        return errors

    def process(self, context: FlowContext) -> FlowContext:
        # Safe to use self.connection_string and self.table_name
        ...
```

Validation is called during engine initialization:

```python
engine = FlowEngine(config, components)
errors = engine.validate()
if errors:
    print("Configuration errors:", errors)
```

---

## Health Checks

Implement `health_check()` to verify component readiness:

```python
class APIComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.base_url = config["base_url"]

    def health_check(self) -> bool:
        try:
            response = requests.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
```

Check health before execution:

```python
for name, component in components.items():
    if not component.health_check():
        print(f"Component {name} is not healthy!")
```

---

## Timeout Compliance

For long-running operations, call `check_deadline()` periodically:

```python
class BatchProcessor(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        items = context.get("items", [])
        results = []

        for item in items:
            # Check if we've exceeded the deadline
            self.check_deadline(context)

            # Process item
            result = self.process_item(item)
            results.append(result)

        context.set("results", results)
        return context
```

!!! warning
    If `require_deadline_check: true` is set in flow settings and your component doesn't call `check_deadline()`, a `DeadlineCheckError` will be raised.

---

## Complete Example

```python
from flowengine import BaseComponent, FlowContext

class ETLComponent(BaseComponent):
    """Complete ETL component with full lifecycle."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.source_table = config.get("source_table")
        self.target_table = config.get("target_table")
        self.batch_size = config.get("batch_size", 1000)
        self._conn = None

    def validate_config(self) -> list[str]:
        errors = []
        if not self.source_table:
            errors.append("source_table is required")
        if not self.target_table:
            errors.append("target_table is required")
        return errors

    def health_check(self) -> bool:
        # Would check database connectivity
        return True

    def setup(self, context: FlowContext) -> None:
        self._conn = create_db_connection()

    def process(self, context: FlowContext) -> FlowContext:
        # Extract
        data = self._conn.query(f"SELECT * FROM {self.source_table}")

        # Transform with deadline checks
        transformed = []
        for i, record in enumerate(data):
            if i % 100 == 0:
                self.check_deadline(context)
            transformed.append(self.transform_record(record))

        # Load
        self._conn.bulk_insert(self.target_table, transformed)

        context.set("rows_processed", len(transformed))
        return context

    def teardown(self, context: FlowContext) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    def transform_record(self, record):
        # Transform logic
        return record
```

---

## Async Components

Components can implement native async processing by overriding `process_async()`:

```python
import asyncio
from flowengine import BaseComponent, FlowContext

class AsyncAPIComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        # Sync fallback (used when async is not available)
        context.set("result", sync_fetch())
        return context

    async def process_async(self, context: FlowContext) -> FlowContext:
        # Native async implementation
        result = await async_fetch()
        context.set("result", result)
        return context
```

### is_async Property

Detect whether a component supports async:

```python
comp = AsyncAPIComponent("api")
print(comp.is_async)  # True — process_async is overridden

sync_comp = SimpleComponent("sync")
print(sync_comp.is_async)  # False — only process() defined
```

### Default Fallback

If a component does **not** override `process_async()`, calling it will automatically run the synchronous `process()` method. This means all components can be used in async contexts.

---

## Port-Based Output Routing

In graph flows, components can direct execution to specific downstream branches using output ports:

```python
class RouterComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        request_type = context.get("request_type")

        if request_type == "urgent":
            self.set_output_port(context, "urgent")
        else:
            self.set_output_port(context, "normal")

        return context
```

The `set_output_port(context, port_name)` method sets the active port on the context. The graph executor then only activates edges whose `port` field matches the active port (plus any unconditional edges with no port).

### Low-Level Port API

You can also use the context's port methods directly:

```python
context.set_port("my_port")          # Set active port
port = context.get_active_port()     # Get active port (or None)
context.clear_port()                 # Clear active port
```

---

## Best Practices

1. **Always call `super().init(config)`** in your `init()` method
2. **Always return the context** from `process()`
3. **Use `setup()` for connections**, not `init()`
4. **Always close resources** in `teardown()`
5. **Call `check_deadline()`** in loops for long operations
6. **Validate configuration** in `validate_config()`
7. **Keep components focused** - one responsibility per component
8. **Use `set_output_port()`** for graph branching instead of manipulating context flags
9. **Override `process_async()`** for I/O-bound components that benefit from async
