# Frequently Asked Questions

Common questions and answers about FlowEngine.

---

## General

### What is FlowEngine?

FlowEngine is a lightweight, YAML-driven state machine for Python. It allows you to define execution flows declaratively in YAML, with business logic implemented in Python components.

### When should I use FlowEngine?

FlowEngine is ideal for:

- **Data pipelines**: ETL workflows, data processing
- **Request routing**: API request dispatch, multi-tenant routing
- **Workflow automation**: Business process automation
- **Conditional processing**: Complex branching logic

### What are the requirements?

- Python 3.11+
- pyyaml >= 6.0
- pydantic >= 2.0

---

## Configuration

### Can I use environment variables in YAML?

Yes, you can reference environment variables in your YAML:

```yaml
components:
  - name: api
    type: myapp.APIComponent
    config:
      api_key: "${API_KEY}"
```

And handle them in your component:

```python
import os

def init(self, config):
    super().init(config)
    api_key = config.get("api_key", "")
    if api_key.startswith("${"):
        env_var = api_key[2:-1]
        self.api_key = os.environ.get(env_var, "")
    else:
        self.api_key = api_key
```

### How do I validate my YAML configuration?

```python
from flowengine import ConfigLoader, ConfigurationError

try:
    config = ConfigLoader.load("flow.yaml")
    print("Configuration is valid!")
except ConfigurationError as e:
    print(f"Configuration error: {e.message}")
    for detail in e.details:
        print(f"  - {detail}")
```

### What's the difference between sequential and conditional flows?

| Type | Behavior |
|------|----------|
| Sequential | All steps run if their conditions match |
| Conditional | First matching step runs, then stops |

Use **sequential** for pipelines where multiple steps should execute.
Use **conditional** for routing/dispatch where only one path should execute.

---

## Components

### How do I share data between components?

Use the `FlowContext`:

```python
# Component 1: Set data
context.set("user", {"name": "Alice"})

# Component 2: Get data
user = context.get("user")
```

### Can a component be used multiple times in a flow?

Yes! The same component instance can appear in multiple steps:

```yaml
steps:
  - component: logger
    description: "Log before processing"

  - component: processor

  - component: logger
    description: "Log after processing"
```

### How do I handle component initialization errors?

Use `validate_config()`:

```python
class MyComponent(BaseComponent):
    def validate_config(self) -> list[str]:
        errors = []
        if not self.config.get("required_field"):
            errors.append("required_field is required")
        return errors
```

Then validate before execution:

```python
errors = engine.validate()
if errors:
    print("Validation errors:", errors)
```

---

## Conditions

### Why can't I use function calls in conditions?

For security. Function calls could execute arbitrary code:

```yaml
# NOT allowed (security risk)
condition: "os.system('rm -rf /')"
```

Instead, compute values in components and check the results:

```yaml
# Allowed
condition: "context.data.is_valid == True"
```

### How do I check if a list is empty?

You can't use `len()`, but you can check for None:

```yaml
# Check if list exists and is not None
condition: "context.data.items is not None"
```

Or set an explicit flag in your component:

```python
context.set("has_items", len(items) > 0)
```

```yaml
condition: "context.data.has_items == True"
```

### What operators are allowed in conditions?

- Comparisons: `==`, `!=`, `<`, `<=`, `>`, `>=`
- Logical: `and`, `or`, `not`
- Identity: `is`, `is not`
- Membership: `in`, `not in`

---

## Timeouts

### Which timeout mode should I use?

| Situation | Mode |
|-----------|------|
| Components call `check_deadline()` | `cooperative` (default) |
| I/O-bound operations | `hard_async` |
| CPU-bound that might hang | `hard_process` |

### What happens when a timeout occurs?

1. `FlowTimeoutError` is raised
2. Teardown runs for the current component
3. Execution stops
4. You can catch the error and handle it

### How do I implement cooperative timeout?

Call `check_deadline()` periodically:

```python
def process(self, context):
    for i, item in enumerate(items):
        if i % 100 == 0:
            self.check_deadline(context)
        process_item(item)
    return context
```

---

## Error Handling

### How do I continue after an error?

Set `fail_fast: false` and use `on_error`:

```yaml
flow:
  settings:
    fail_fast: false

  steps:
    - component: risky_step
      on_error: continue
```

### How do I access errors after execution?

```python
result = engine.execute()

if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"{error['component']}: {error['message']}")
```

### Can I run a step only if there were errors?

Yes:

```yaml
steps:
  - component: main_process
    on_error: continue

  - component: error_handler
    condition: "context.metadata.has_errors == True"
```

---

## Performance

### How do I measure step performance?

Access timing metadata:

```python
result = engine.execute()

for timing in result.metadata.step_timings:
    print(f"{timing.component}: {timing.duration:.3f}s")
```

### Is there overhead for using FlowEngine?

Minimal. The main overhead is:

- YAML parsing (once at startup)
- Condition evaluation (microseconds per step)
- Metadata tracking (minimal)

For typical flows, overhead is negligible compared to actual component work.

---

## Debugging

### How do I debug a flow?

1. Use `LoggingComponent` to inspect state:

```yaml
- component: debug_logger
  type: flowengine.contrib.logging.LoggingComponent
  config:
    level: debug
    log_data: true
```

2. Use `dry_run()` to preview execution:

```python
steps = engine.dry_run(context)
print("Would run:", steps)
```

3. Serialize context on error:

```python
try:
    result = engine.execute()
except Exception as e:
    with open("debug.json", "w") as f:
        f.write(context.to_json())
```

### How do I see which steps were skipped?

```python
result = engine.execute()
print("Skipped:", result.metadata.skipped_components)
```

---

## Integration

### Can I use FlowEngine with async code?

FlowEngine runs synchronously, but you can:

1. Use `hard_async` timeout mode for I/O operations
2. Call FlowEngine from async code:

```python
import asyncio

async def run_flow():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, engine.execute)
    return result
```

### Can I use FlowEngine with FastAPI/Flask?

Yes! Example with FastAPI:

```python
from fastapi import FastAPI
from flowengine import FlowEngine, ConfigLoader

app = FastAPI()
config = ConfigLoader.load("flow.yaml")
engine = FlowEngine.from_config(config)

@app.post("/process")
def process_request(data: dict):
    context = FlowContext()
    context.set("request", data)
    result = engine.execute(context)
    return result.data.to_dict()
```

---

## Still Have Questions?

- Check the [User Guide](user-guide/components.md)
- Browse the [API Reference](api/index.md)
- Open a [GitHub Issue](https://github.com/yourorg/flowengine/issues)
