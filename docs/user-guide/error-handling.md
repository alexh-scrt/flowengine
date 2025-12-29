# Error Handling

FlowEngine provides flexible error handling at both the flow and step level, allowing you to build resilient workflows.

---

## Error Handling Levels

### Flow Level: `fail_fast`

Controls whether execution stops on the first error:

```yaml
flow:
  settings:
    fail_fast: true  # Stop on first error (default)
```

| Value | Behavior |
|-------|----------|
| `true` | Stop execution on first error, raise exception |
| `false` | Continue execution, collect errors in metadata |

### Step Level: `on_error`

Controls how individual step errors are handled:

```yaml
steps:
  - component: risky_operation
    on_error: continue  # fail, skip, or continue
```

| Value | Behavior |
|-------|----------|
| `fail` | Stop execution, raise exception (default) |
| `skip` | Log error, mark step as skipped |
| `continue` | Log error, continue to next step |

### Condition Level: `on_condition_error`

Controls how condition evaluation errors are handled:

```yaml
flow:
  settings:
    on_condition_error: fail  # fail, skip, or warn
```

| Value | Behavior |
|-------|----------|
| `fail` | Raise `ConditionEvaluationError` (default) |
| `skip` | Skip the step, log error |
| `warn` | Skip the step, log warning |

---

## Exception Hierarchy

```
FlowEngineError (base)
├── ConfigurationError      # Invalid YAML, schema errors
├── FlowExecutionError      # Runtime execution errors
│   ├── FlowTimeoutError    # Timeout exceeded
│   └── DeadlineCheckError  # Component didn't check deadline
├── ComponentError          # Component processing error
└── ConditionEvaluationError # Invalid/unsafe condition
```

### Exception Attributes

```python
from flowengine import (
    FlowEngineError,
    ConfigurationError,
    FlowExecutionError,
    FlowTimeoutError,
    DeadlineCheckError,
    ComponentError,
    ConditionEvaluationError,
)

# ConfigurationError
try:
    config = ConfigLoader.load("invalid.yaml")
except ConfigurationError as e:
    print(e.message)
    print(e.config_path)  # Path to config file
    print(e.details)      # List of validation errors

# FlowTimeoutError
try:
    result = engine.execute()
except FlowTimeoutError as e:
    print(e.message)
    print(e.timeout)   # Configured timeout
    print(e.elapsed)   # Actual elapsed time
    print(e.flow_id)   # Execution ID
    print(e.step)      # Step where timeout occurred

# DeadlineCheckError
try:
    result = engine.execute()
except DeadlineCheckError as e:
    print(e.message)
    print(e.component)  # Component name
    print(e.duration)   # How long it ran
    print(e.threshold)  # Warning threshold

# ComponentError
try:
    result = engine.execute()
except ComponentError as e:
    print(e.message)
    print(e.component)      # Component name
    print(e.original_error) # Underlying exception

# ConditionEvaluationError
try:
    result = engine.execute()
except ConditionEvaluationError as e:
    print(e.message)
    print(e.condition)  # The invalid condition
```

---

## Accessing Errors in Metadata

With `fail_fast: false`, errors are collected in context metadata:

```python
flow:
  settings:
    fail_fast: false

result = engine.execute()

# Check for errors
if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"Component: {error['component']}")
        print(f"Error: {error['message']}")
        print(f"Type: {error['error_type']}")
        print(f"Timestamp: {error['timestamp']}")

# Check for condition errors
if result.metadata.has_condition_errors:
    for error in result.metadata.condition_errors:
        print(f"Component: {error['component']}")
        print(f"Condition: {error['condition']}")
        print(f"Error: {error['message']}")
```

---

## Error Handling Patterns

### Try Everything, Report All Errors

```yaml
flow:
  settings:
    fail_fast: false

  steps:
    - component: step1
      on_error: continue

    - component: step2
      on_error: continue

    - component: step3
      on_error: continue

    - component: error_reporter
      condition: "context.metadata.has_errors == True"
```

### Critical Path with Optional Steps

```yaml
flow:
  settings:
    fail_fast: true  # Stop on critical errors

  steps:
    - component: critical_step
      on_error: fail  # Must succeed

    - component: optional_enhancement
      on_error: skip  # Nice to have

    - component: another_critical
      on_error: fail
```

### Fallback Pattern

```yaml
flow:
  type: sequential
  settings:
    fail_fast: false

  steps:
    - component: primary_source
      on_error: skip

    - component: fallback_source
      condition: "context.data.primary_data is None"
      on_error: fail

    - component: process_data
      condition: "context.data.primary_data is not None or context.data.fallback_data is not None"
```

### Error Recovery Flow

```yaml
flow:
  settings:
    fail_fast: false

  steps:
    - component: main_process
      on_error: continue

    - component: recovery_process
      condition: "context.metadata.has_errors == True"
      on_error: continue

    - component: notify_success
      condition: "context.metadata.has_errors == False"

    - component: notify_failure
      condition: "context.metadata.has_errors == True"
```

---

## Programmatic Error Handling

### Basic Try/Except

```python
from flowengine import FlowEngine, FlowExecutionError

try:
    result = engine.execute()
    print("Success:", result.data.result)
except FlowExecutionError as e:
    print(f"Execution failed: {e.message}")
    print(f"Step: {e.step}")
```

### Comprehensive Handling

```python
from flowengine import (
    FlowEngine,
    ConfigurationError,
    FlowTimeoutError,
    DeadlineCheckError,
    ComponentError,
    ConditionEvaluationError,
)

try:
    config = ConfigLoader.load("flow.yaml")
    engine = FlowEngine(config, components)
    result = engine.execute()

except ConfigurationError as e:
    logging.error(f"Configuration error: {e.message}")
    for detail in e.details:
        logging.error(f"  - {detail}")

except FlowTimeoutError as e:
    logging.error(f"Timeout after {e.elapsed:.2f}s at step '{e.step}'")

except DeadlineCheckError as e:
    logging.error(f"Component '{e.component}' didn't check deadline")
    logging.error(f"Ran for {e.duration:.2f}s (threshold: {e.threshold}s)")

except ComponentError as e:
    logging.error(f"Component '{e.component}' failed: {e.message}")
    if e.original_error:
        logging.exception(e.original_error)

except ConditionEvaluationError as e:
    logging.error(f"Invalid condition: {e.condition}")
    logging.error(f"Error: {e.message}")
```

---

## Component-Level Error Handling

### Validation Errors

```python
class MyComponent(BaseComponent):
    def validate_config(self) -> list[str]:
        errors = []
        if not self.config.get("required_field"):
            errors.append("required_field is required")
        return errors
```

### Processing Errors

```python
class ResilientComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        try:
            result = self.risky_operation()
            context.set("result", result)
            context.set("status", "success")
        except SpecificError as e:
            # Handle known error
            context.set("status", "partial")
            context.set("error", str(e))
        except Exception as e:
            # Re-raise unknown errors
            raise ComponentError(
                f"Unexpected error in {self.name}",
                component=self.name,
                original_error=e,
            )
        return context
```

### Cleanup in Teardown

```python
class ResourceComponent(BaseComponent):
    def setup(self, context: FlowContext) -> None:
        self._conn = open_connection()

    def process(self, context: FlowContext) -> FlowContext:
        # May raise exception
        data = self._conn.query()
        context.set("data", data)
        return context

    def teardown(self, context: FlowContext) -> None:
        # Always runs, even if process() failed
        if self._conn:
            self._conn.close()
            self._conn = None
```

---

## Best Practices

1. **Use `fail_fast: false`** for flows that should collect all errors
2. **Use `on_error: skip`** for optional enhancement steps
3. **Use `on_error: continue`** for steps that must run regardless
4. **Implement `teardown()`** for resource cleanup
5. **Check `metadata.has_errors`** for conditional error handling steps
6. **Log original errors** when wrapping in `ComponentError`
7. **Validate configuration** in `validate_config()` to fail early

---

## Next Steps

- [Timeout Modes](timeout-modes.md) - Handle timeout errors
- [Components](components.md) - Component error handling
- [API Reference](../api/errors.md) - Exception details
