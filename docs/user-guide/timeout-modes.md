# Timeout Modes

FlowEngine provides three timeout enforcement modes to protect against runaway flows and ensure predictable execution times.

---

## Overview

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: cooperative  # cooperative, hard_async, or hard_process
```

| Mode | Enforcement | Best For |
|------|-------------|----------|
| `cooperative` | Components call `check_deadline()` | Default, safest for complex components |
| `hard_async` | Uses `asyncio.wait_for` | I/O-bound operations |
| `hard_process` | Runs in separate process | CPU-bound, guaranteed termination |

---

## Cooperative Mode (Default)

Components voluntarily check if the deadline has passed.

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: cooperative
```

### How It Works

1. Engine sets a deadline before each step
2. Engine checks deadline between steps
3. Components call `check_deadline()` during long operations
4. If deadline exceeded, `FlowTimeoutError` is raised

### Component Implementation

```python
class BatchProcessor(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        items = context.get("items", [])
        results = []

        for i, item in enumerate(items):
            # Check every N iterations
            if i % 100 == 0:
                self.check_deadline(context)

            results.append(self.process_item(item))

        context.set("results", results)
        return context
```

### Strict Enforcement

With `require_deadline_check: true`, components **must** call `check_deadline()`:

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: cooperative
    require_deadline_check: true
```

If a component runs longer than a threshold (default 1 second) without calling `check_deadline()`, a `DeadlineCheckError` is raised.

```python
from flowengine import DeadlineCheckError

try:
    result = engine.execute()
except DeadlineCheckError as e:
    print(f"Component '{e.component}' didn't check deadline")
    print(f"Ran for {e.duration:.2f}s")
```

---

## Hard Async Mode

Uses `asyncio.wait_for` to enforce timeouts. Components run in a thread executor, allowing cancellation of blocking operations.

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: hard_async
```

### How It Works

1. Each step runs in a thread via asyncio
2. `asyncio.wait_for` enforces the timeout
3. On timeout, the task is cancelled
4. Teardown always runs in the main thread

### When to Use

- I/O-bound operations (network, file system)
- Components that block on external resources
- When you can't modify components to call `check_deadline()`

### Limitations

- Cannot interrupt pure CPU-bound operations
- Thread may continue briefly after cancellation
- Not suitable for infinite loops

---

## Hard Process Mode

Runs each step in a separate process with hard kill on timeout.

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: hard_process
```

### How It Works

1. Each step runs in a separate process
2. Process is killed if it exceeds timeout
3. Context is serialized/deserialized across process boundary
4. Teardown runs in main process after process terminates

### When to Use

- CPU-bound operations that may hang
- Untrusted or third-party components
- When guaranteed termination is required

### Requirements

- Components must be picklable
- Context data must be JSON-serializable
- Higher overhead than other modes

```python
# Works - standard class
class SafeComponent(BaseComponent):
    def process(self, context):
        ...

# Doesn't work - lambda not picklable
class UnsafeComponent(BaseComponent):
    def init(self, config):
        self.transform = lambda x: x * 2  # Can't pickle
```

---

## Comparison

| Scenario | Cooperative | Hard Async | Hard Process |
|----------|-------------|------------|--------------|
| Between steps | ✅ Always | ✅ Always | ✅ Always |
| Component calls `check_deadline()` | ✅ Yes | ✅ Yes | ✅ Yes |
| Component blocks without checking | ❌ Overruns | ✅ Cancelled | ✅ Killed |
| Teardown runs on timeout | ✅ Yes | ✅ Yes | ✅ Yes |
| Overhead | Low | Medium | High |
| CPU-bound protection | ❌ No | ❌ No | ✅ Yes |

---

## Choosing a Mode

```
┌─────────────────────────────────────────────────────────┐
│                Choose Timeout Mode                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Components call check_deadline()?                      │
│    └── YES → Use cooperative (default, safest)          │
│    └── NO  → Components do I/O operations?              │
│                └── YES → Use hard_async                 │
│                └── NO  → Components are CPU-bound?      │
│                            └── YES → Use hard_process   │
│                            └── NO  → Use cooperative    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Error Handling

```python
from flowengine import FlowTimeoutError, DeadlineCheckError

try:
    result = engine.execute()
except FlowTimeoutError as e:
    print(f"Timeout after {e.elapsed:.2f}s (limit: {e.timeout}s)")
    print(f"Message: {e.message}")
except DeadlineCheckError as e:
    print(f"Component '{e.component}' didn't check deadline")
    print(f"Duration: {e.duration:.2f}s")
```

---

## Best Practices

### Cooperative Mode

```python
class CooperativeComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        # Check before long operations
        self.check_deadline(context)
        data = fetch_large_dataset()

        # Check in loops
        for i, item in enumerate(data):
            if i % 100 == 0:
                self.check_deadline(context)
            process(item)

        # Check before I/O
        self.check_deadline(context)
        save_results()

        return context
```

### Hard Async Mode

```python
class AsyncSafeComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        # I/O operations are interruptible
        response = requests.get(self.url, timeout=10)
        context.set("data", response.json())
        return context
```

### Hard Process Mode

```python
class ProcessSafeComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        # Only store serializable data
        self.url = config["url"]
        self.timeout = config.get("timeout", 30)

    def process(self, context: FlowContext) -> FlowContext:
        # Will be killed if timeout exceeded
        result = expensive_cpu_operation()
        context.set("result", result)
        return context
```

---

## Configuration Examples

### Development (Fast Fail)

```yaml
flow:
  settings:
    timeout_seconds: 10
    timeout_mode: cooperative
    require_deadline_check: true
```

### Production (Resilient)

```yaml
flow:
  settings:
    timeout_seconds: 300
    timeout_mode: hard_async
```

### Untrusted Components

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: hard_process
```

---

## Next Steps

- [Error Handling](error-handling.md) - Handle timeout errors
- [Components](components.md) - Implement `check_deadline()`
- [API Reference](../api/errors.md) - Exception details
