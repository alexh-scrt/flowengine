# Errors Module

Exception hierarchy and error handling.

---

## Exception Hierarchy

```
FlowEngineError (base)
├── ConfigurationError      # Invalid configuration
├── FlowExecutionError      # Runtime execution errors
│   ├── FlowTimeoutError    # Timeout exceeded
│   └── DeadlineCheckError  # Component didn't check deadline
├── ComponentError          # Component processing error
└── ConditionEvaluationError # Invalid/unsafe condition
```

---

## FlowEngineError

Base exception for all FlowEngine errors.

::: flowengine.errors.exceptions.FlowEngineError
    options:
      show_source: false
      members:
        - __init__
        - message

---

## ConfigurationError

Raised for configuration validation errors.

::: flowengine.errors.exceptions.ConfigurationError
    options:
      show_source: false
      members:
        - __init__
        - message
        - config_path
        - details

---

## FlowExecutionError

Raised for runtime execution errors.

::: flowengine.errors.exceptions.FlowExecutionError
    options:
      show_source: false
      members:
        - __init__
        - message
        - flow_id
        - step

---

## FlowTimeoutError

Raised when execution exceeds the configured timeout.

::: flowengine.errors.exceptions.FlowTimeoutError
    options:
      show_source: false
      members:
        - __init__
        - message
        - timeout
        - elapsed

---

## DeadlineCheckError

Raised when a component fails to call `check_deadline()`.

::: flowengine.errors.exceptions.DeadlineCheckError
    options:
      show_source: false
      members:
        - __init__
        - message
        - component
        - duration
        - threshold

---

## ComponentError

Raised when a component fails during processing.

::: flowengine.errors.exceptions.ComponentError
    options:
      show_source: false
      members:
        - __init__
        - message
        - component
        - original_error

---

## ConditionEvaluationError

Raised for invalid or unsafe condition expressions.

::: flowengine.errors.exceptions.ConditionEvaluationError
    options:
      show_source: false
      members:
        - __init__
        - message
        - condition

---

## Usage Examples

### Catching Specific Errors

```python
from flowengine import (
    FlowEngine,
    ConfigLoader,
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
    print(f"Config error: {e.message}")
    print(f"File: {e.config_path}")
    for detail in e.details:
        print(f"  - {detail}")

except FlowTimeoutError as e:
    print(f"Timeout at step '{e.step}'")
    print(f"Elapsed: {e.elapsed:.2f}s")
    print(f"Limit: {e.timeout}s")

except DeadlineCheckError as e:
    print(f"Component '{e.component}' didn't check deadline")
    print(f"Ran for {e.duration:.2f}s")

except ComponentError as e:
    print(f"Component '{e.component}' failed")
    print(f"Error: {e.message}")
    if e.original_error:
        print(f"Cause: {e.original_error}")

except ConditionEvaluationError as e:
    print(f"Invalid condition: {e.condition}")
    print(f"Error: {e.message}")
```

### Raising Custom Errors

```python
from flowengine import ComponentError, BaseComponent, FlowContext

class MyComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        try:
            result = self.risky_operation()
        except ValueError as e:
            raise ComponentError(
                f"Invalid value in {self.name}",
                component=self.name,
                original_error=e,
            )
        context.set("result", result)
        return context
```

### Checking Error Attributes

```python
try:
    result = engine.execute()
except FlowTimeoutError as e:
    # All attributes available
    print(f"Message: {e.message}")
    print(f"Flow ID: {e.flow_id}")
    print(f"Step: {e.step}")
    print(f"Timeout: {e.timeout}")
    print(f"Elapsed: {e.elapsed}")

    # Can re-raise with additional context
    raise RuntimeError(f"Flow timed out at {e.step}") from e
```

### Error Recovery Pattern

```python
from flowengine import FlowEngineError

def execute_with_retry(engine, max_retries=3):
    for attempt in range(max_retries):
        try:
            return engine.execute()
        except FlowTimeoutError:
            if attempt == max_retries - 1:
                raise
            print(f"Retry {attempt + 1}/{max_retries}")
        except FlowEngineError:
            # Don't retry other errors
            raise
```
