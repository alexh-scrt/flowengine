# Context Serialization

FlowEngine supports full round-trip serialization of `FlowContext`, enabling debugging, replay, and persistence.

---

## Overview

The entire context state - including data, metadata, timing, and errors - can be serialized to JSON and restored later.

```python
# After execution
result = engine.execute()

# Serialize
json_str = result.to_json()

# Later, restore
restored = FlowContext.from_json(json_str)
```

---

## Serialization Methods

### To JSON String

```python
from flowengine import FlowContext

context = FlowContext()
context.set("user", {"name": "Alice", "id": 123})

# Serialize to JSON
json_str = context.to_json(indent=2)
print(json_str)
```

Output:

```json
{
  "data": {
    "user": {
      "name": "Alice",
      "id": 123
    }
  },
  "metadata": {
    "flow_id": "abc123",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": null,
    "step_timings": [],
    "skipped_components": [],
    "errors": [],
    "condition_errors": []
  },
  "input": null
}
```

### To Dictionary

```python
# Convert to dict
data = context.to_dict()

# Use with standard JSON library
import json
json_str = json.dumps(data, default=str)
```

### From JSON String

```python
json_str = '{"data": {"key": "value"}, "metadata": {...}}'
context = FlowContext.from_json(json_str)
```

### From Dictionary

```python
data = {
    "data": {"key": "value"},
    "metadata": {"flow_id": "abc123"},
}
context = FlowContext.from_dict(data)
```

---

## What Gets Serialized

### Data

All values in `context.data`:

```python
context.set("string", "value")
context.set("number", 42)
context.set("float", 3.14)
context.set("boolean", True)
context.set("none", None)
context.set("list", [1, 2, 3])
context.set("dict", {"nested": "value"})
```

### Metadata

Execution metadata:

```python
{
    "flow_id": "unique-execution-id",
    "started_at": "2024-01-15T10:30:00Z",
    "completed_at": "2024-01-15T10:30:05Z",
    "step_timings": [
        {
            "step_index": 0,
            "component": "fetch",
            "duration": 1.234,
            "started_at": "2024-01-15T10:30:00Z",
            "execution_order": 0
        }
    ],
    "skipped_components": ["optional_step"],
    "errors": [
        {
            "component": "processor",
            "message": "Failed to process",
            "error_type": "ValueError",
            "timestamp": "2024-01-15T10:30:03Z"
        }
    ],
    "condition_errors": []
}
```

### Input

Original input data:

```python
context = FlowContext(input={"request_id": "abc123"})
```

---

## Use Cases

### Debugging Failed Flows

Save context on error for later analysis:

```python
from flowengine import FlowEngine, FlowExecutionError

try:
    result = engine.execute()
except FlowExecutionError as e:
    # Save the current context state
    with open(f"debug_{e.flow_id}.json", "w") as f:
        f.write(engine._current_context.to_json(indent=2))
    raise
```

### Replay Execution

Replay a flow from a saved state:

```python
# Load saved context
with open("saved_context.json") as f:
    saved = FlowContext.from_json(f.read())

# Resume execution from this state
result = engine.execute(context=saved)
```

### Checkpointing

Save progress for long-running flows:

```python
class CheckpointComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.checkpoint_path = config["checkpoint_path"]

    def process(self, context: FlowContext) -> FlowContext:
        # Save checkpoint
        with open(self.checkpoint_path, "w") as f:
            f.write(context.to_json())
        return context
```

### Audit Trail

Store execution history:

```python
import datetime

def log_execution(result: FlowContext) -> None:
    timestamp = datetime.datetime.now().isoformat()
    filename = f"audit/{result.metadata.flow_id}_{timestamp}.json"

    with open(filename, "w") as f:
        f.write(result.to_json(indent=2))
```

### Testing

Use serialized contexts for testing:

```python
def test_component_with_saved_context():
    # Load a known context state
    with open("test_fixtures/sample_context.json") as f:
        context = FlowContext.from_json(f.read())

    component = MyComponent("test")
    result = component.process(context)

    assert result.data.expected_key == "expected_value"
```

---

## Handling Non-Serializable Data

### Custom Objects

If your context contains non-JSON-serializable objects, convert them first:

```python
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def to_dict(self):
        return {"name": self.name, "email": self.email}

class UserComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        user = User("Alice", "alice@example.com")
        # Store as dict for serialization
        context.set("user", user.to_dict())
        return context
```

### DateTime Objects

Datetime objects are automatically converted to ISO format strings:

```python
import datetime

context.set("timestamp", datetime.datetime.now())
json_str = context.to_json()
# timestamp stored as "2024-01-15T10:30:00.000000"
```

### Binary Data

Encode binary data before storing:

```python
import base64

context.set("image", base64.b64encode(image_bytes).decode())
```

---

## Context Copy

Create a shallow copy of a context:

```python
original = FlowContext()
original.set("key", "value")

# Create copy
copy = original.copy()

# Modify copy without affecting original
copy.set("key", "new_value")
copy.set("new_key", "another_value")

print(original.data.key)  # "value"
print(copy.data.key)      # "new_value"
```

---

## Best Practices

1. **Store serializable data**: Use dicts, lists, strings, numbers, booleans, None
2. **Convert custom objects**: Implement `to_dict()` methods
3. **Validate restored context**: Check required keys exist after restore
4. **Use meaningful flow IDs**: Include timestamp or request ID
5. **Compress large contexts**: Use gzip for storage
6. **Clean up old checkpoints**: Implement retention policy

---

## Next Steps

- [Architecture](architecture.md) - Internal design
- [Context Guide](../user-guide/context.md) - Working with context
- [API Reference](../api/core.md) - FlowContext API
