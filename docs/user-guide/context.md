# FlowContext & Data Flow

The `FlowContext` is the central data carrier in FlowEngine. It passes through all components, accumulating data and tracking execution metadata.

---

## FlowContext Overview

```python
from flowengine import FlowContext

context = FlowContext()
```

A context has three main parts:

| Attribute | Type | Purpose |
|-----------|------|---------|
| `data` | `DotDict` | Main data container |
| `metadata` | `ExecutionMetadata` | Timing, errors, execution state |
| `input` | `Any` | Optional initial input data |

Plus v0.2.0 additions for graph flow support:

| Method | Purpose |
|--------|---------|
| `set_port(port)` | Set the active output port for routing |
| `get_active_port()` | Get current active port (or `None`) |
| `clear_port()` | Clear the active port |
| `suspend(node_id, reason)` | Suspend flow execution at a node |

---

## Working with Data

### Setting Values

```python
context.set("user", {"name": "Alice", "id": 123})
context.set("count", 42)
context.set("tags", ["python", "workflow"])
```

### Getting Values

```python
# Get with default
name = context.get("user", {}).get("name")

# Get with fallback
count = context.get("count", 0)

# Check existence
if context.has("user"):
    user = context.get("user")
```

### Deleting Values

```python
context.delete("temporary_data")
```

---

## DotDict: Attribute-Style Access

The `context.data` object is a `DotDict` - a dictionary that allows attribute-style access:

```python
context.set("user", {"name": "Alice", "profile": {"age": 30}})

# Attribute-style access (dot notation)
print(context.data.user.name)           # "Alice"
print(context.data.user.profile.age)    # 30

# Also works in conditions
# condition: "context.data.user.profile.age >= 18"
```

### DotDict Methods

```python
# Get all keys
keys = context.data.keys()

# Get all values
values = context.data.values()

# Get items
for key, value in context.data.items():
    print(f"{key}: {value}")

# Convert to regular dict
regular_dict = context.data.to_dict()

# Update with another dict
context.data.update({"new_key": "new_value"})
```

---

## Initial Input Data

Pass initial data when creating the context:

```python
# Using FlowContext constructor
context = FlowContext(input={"request_id": "abc123"})

# Or using engine.execute()
result = engine.execute(input_data={"request_id": "abc123"})
```

Access the original input:

```python
def process(self, context: FlowContext) -> FlowContext:
    request_id = context.input.get("request_id")
    # ...
```

---

## Execution Metadata

The context automatically tracks execution information:

```python
result = engine.execute()

# Unique execution ID
print(result.metadata.flow_id)  # "f47ac10b-58cc-4372-a567-0e02b2c3d479"

# Timing
print(result.metadata.started_at)      # datetime
print(result.metadata.completed_at)    # datetime
print(result.metadata.total_duration)  # 1.234 (seconds)

# Per-step timing
for timing in result.metadata.step_timings:
    print(f"{timing.component}: {timing.duration:.3f}s")

# Aggregated by component
for name, total in result.metadata.component_timings.items():
    print(f"{name}: {total:.3f}s total")
```

### StepTiming Details

Each step timing includes:

```python
for timing in result.metadata.step_timings:
    print(f"Step {timing.step_index}")        # Position in flow (0-based)
    print(f"Component: {timing.component}")    # Component name
    print(f"Duration: {timing.duration:.4f}s") # Execution time
    print(f"Started: {timing.started_at}")     # When it started
    print(f"Order: {timing.execution_order}")  # Execution sequence
```

### Error Tracking

```python
if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"Component: {error['component']}")
        print(f"Error: {error['message']}")
        print(f"Type: {error['error_type']}")

# Condition evaluation errors
if result.metadata.has_condition_errors:
    for error in result.metadata.condition_errors:
        print(f"Component: {error['component']}")
        print(f"Condition: {error['condition']}")
        print(f"Error: {error['message']}")
```

### Skipped Components

```python
skipped = result.metadata.skipped_components
print(f"Skipped: {skipped}")  # ["optional_step", "fallback_step"]
```

---

## Context Serialization

Contexts can be fully serialized for replay, debugging, or persistence:

### To JSON

```python
# Serialize
json_str = result.to_json(indent=2)

# Save to file
with open("context_snapshot.json", "w") as f:
    f.write(json_str)
```

### From JSON

```python
# Load from file
with open("context_snapshot.json") as f:
    json_str = f.read()

# Restore
restored = FlowContext.from_json(json_str)

# All data preserved
print(restored.data.user.name)
print(restored.metadata.flow_id)
print(restored.metadata.step_timings)
```

### To/From Dict

```python
# To dict
data = context.to_dict()

# From dict
restored = FlowContext.from_dict(data)
```

---

## Context Copy

Create a shallow copy of the context:

```python
context_copy = context.copy()

# Modify without affecting original
context_copy.set("new_key", "new_value")
```

---

## Data Flow Patterns

### Pipeline Pattern

Each component reads from previous and writes for next:

```python
class FetchComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        data = fetch_from_api()
        context.set("raw_data", data)
        return context

class TransformComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        raw = context.get("raw_data")
        transformed = transform(raw)
        context.set("transformed_data", transformed)
        return context

class SaveComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("transformed_data")
        save_to_db(data)
        context.set("save_status", "success")
        return context
```

### Accumulator Pattern

Build up results across steps:

```python
class InitComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        context.set("results", [])
        return context

class ProcessorComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        results = context.get("results", [])
        results.append(self.process_item())
        context.set("results", results)
        return context
```

### Status Flag Pattern

Use flags to control conditional execution:

```python
class ValidateComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("input_data")

        if self.is_valid(data):
            context.set("validation_passed", True)
            context.set("validated_data", data)
        else:
            context.set("validation_passed", False)
            context.set("validation_errors", self.get_errors())

        return context
```

```yaml
steps:
  - component: validate

  - component: process_valid
    condition: "context.data.validation_passed == True"

  - component: handle_invalid
    condition: "context.data.validation_passed == False"
```

---

## Port-Based Routing

In graph flows, components signal which branch to take by setting an output port on the context:

```python
class DecisionComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        score = context.get("score", 0)

        if score >= 80:
            context.set_port("high")
        elif score >= 50:
            context.set_port("medium")
        else:
            context.set_port("low")

        return context
```

Or use the helper method on `BaseComponent`:

```python
self.set_output_port(context, "high")
```

The graph executor clears the active port before each node, so ports only apply to the current node's outgoing edges.

### Port Methods

```python
context.set_port("my_port")          # Set active port
port = context.get_active_port()     # Returns "my_port"
context.clear_port()                 # Clears port (returns to None)
```

---

## Flow Suspension

Components can suspend flow execution mid-way, useful for human-in-the-loop patterns:

```python
class ApprovalComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        if not context.has("resume_data"):
            # First run: suspend for human approval
            context.suspend(self.name, reason="Needs human approval")
        else:
            # Resumed: process the approval decision
            decision = context.get("resume_data")
            context.set("approved", decision.get("approved", False))
        return context
```

### Suspension Metadata

When a flow is suspended, the context metadata tracks the state:

```python
result = engine.execute()

if result.metadata.suspended:
    print(f"Suspended at: {result.metadata.suspended_at_node}")
    print(f"Reason: {result.metadata.suspension_reason}")

    # Get the checkpoint ID for later resume
    checkpoint_id = result.get("checkpoint_id")
```

### Completed Nodes

The context tracks which graph nodes have completed, so they can be skipped on resume:

```python
print(result.metadata.completed_nodes)  # ["fetch", "validate"]
```

When a flow resumes, already-completed nodes are skipped. The suspended node re-executes (with `resume_data` available), then execution continues to remaining nodes.

### Serialization

All suspension state is included in context serialization:

```python
d = context.to_dict()
restored = FlowContext.from_dict(d)

assert restored.metadata.suspended == True
assert restored.metadata.completed_nodes == ["fetch", "validate"]
```

---

## Best Practices

1. **Use descriptive keys**: `user_profile` not `up`
2. **Set status flags**: Make conditional logic clear
3. **Don't mutate input**: Treat `context.input` as read-only
4. **Clean up temporary data**: Delete intermediate results if not needed
5. **Leverage metadata**: Use timing data for performance analysis
6. **Serialize for debugging**: Save context snapshots on errors
7. **Never use `_` prefixed keys** for data via `context.set()` — `DotDict` treats them as object attributes, not data keys
8. **Use `set_port()`** for graph routing instead of manual context flags

---

## Next Steps

- [Conditions](conditions.md) - Use context data in conditions
- [Error Handling](error-handling.md) - Handle errors with metadata
- [API Reference](../api/core.md) - Full FlowContext API
