# Flow Configuration

Flows define how components are orchestrated. FlowEngine supports three flow types with different execution semantics.

---

## YAML Structure

A complete flow configuration has three main sections:

```yaml
# Metadata
name: "My Flow"
version: "1.0"
description: "Optional description"

# Component definitions
components:
  - name: component_name
    type: module.path.ComponentClass
    config:
      key: value

# Flow definition
flow:
  type: sequential  # or "conditional" or "graph"
  settings:
    fail_fast: true
    timeout_seconds: 300
  steps:           # For sequential/conditional flows
    - component: component_name
      condition: "context.data.ready == True"
  # OR for graph flows:
  # nodes:
  #   - id: node_id
  #     component: component_name
  # edges:
  #   - source: node_a
  #     target: node_b
```

---

## Flow Types

### Sequential (Default)

Runs **all steps in order**. Each step's condition determines whether that individual step runs.

```yaml
flow:
  type: sequential
  steps:
    - component: fetch_data      # Always runs
    - component: validate_data   # Runs if condition True
      condition: "context.data.fetch_status == 'success'"
    - component: transform_data  # Runs if condition True
      condition: "context.data.is_valid == True"
    - component: save_data       # Runs if condition True
      condition: "context.data.transformed is not None"
```

**All four steps are evaluated.** Multiple steps can execute if their conditions match.

```
Step 1: fetch_data      → Runs (no condition)
Step 2: validate_data   → Runs if fetch_status == 'success'
Step 3: transform_data  → Runs if is_valid == True
Step 4: save_data       → Runs if transformed is not None
```

### Conditional (First-Match)

**First-match branching** like a switch/case statement. Stops after the first step whose condition is True.

```yaml
flow:
  type: conditional
  steps:
    - component: handle_user
      condition: "context.data.request_type == 'user'"
    - component: handle_order
      condition: "context.data.request_type == 'order'"
    - component: handle_admin
      condition: "context.data.request_type == 'admin'"
    - component: handle_unknown  # No condition = default case
```

**Only one step executes.** Once a condition matches, remaining steps are skipped.

```
Input: request_type = "order"

Step 1: handle_user    → Skip (condition False)
Step 2: handle_order   → Run (condition True) ← STOP HERE
Step 3: handle_admin   → Skip (not evaluated)
Step 4: handle_unknown → Skip (not evaluated)
```

---

### Graph (DAG Execution)

Define flows as **directed acyclic graphs** where nodes are components and edges define execution flow. The graph executor uses topological ordering (Kahn's algorithm) to determine execution order.

```yaml
flow:
  type: graph
  settings:
    timeout_seconds: 60
  nodes:
    - id: fetch
      component: fetch_data
    - id: validate
      component: validator
    - id: process
      component: processor
    - id: notify
      component: notifier
  edges:
    - source: fetch
      target: validate
    - source: validate
      target: process
    - source: process
      target: notify
```

```
fetch → validate → process → notify
```

#### Port-Based Routing

Components can signal which output port to activate, enabling conditional branching in graphs:

```python
class ValidatorComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        if is_valid(context.get("data")):
            self.set_output_port(context, "valid")
        else:
            self.set_output_port(context, "invalid")
        return context
```

```yaml
flow:
  type: graph
  nodes:
    - id: fetch
      component: fetch_data
    - id: validate
      component: validator
    - id: process_valid
      component: processor
    - id: handle_invalid
      component: error_handler
  edges:
    - source: fetch
      target: validate
    - source: validate
      target: process_valid
      port: "valid"            # Only activates when port == "valid"
    - source: validate
      target: handle_invalid
      port: "invalid"          # Only activates when port == "invalid"
```

```
               ┌─ [valid] ──→ process_valid
fetch → validate
               └─ [invalid] → handle_invalid
```

**Edge routing rules:**

| Edge Type | Behavior |
|-----------|----------|
| No `port` (unconditional) | Always activates |
| `port: "name"` | Only activates when component sets matching active port |
| No active port set | Only unconditional edges activate |

#### Node Configuration

Each node can have:

```yaml
nodes:
  - id: my_node             # Required: unique node ID
    component: my_component  # Required: component name
    description: "What it does"  # Optional
    on_error: fail           # Optional: fail (default), skip, or continue
```

#### Multiple Root Nodes

Nodes with no incoming edges are root nodes — they all execute first:

```yaml
nodes:
  - id: source_a
    component: fetch_api
  - id: source_b
    component: fetch_db
  - id: merge
    component: merger
edges:
  - source: source_a
    target: merge
  - source: source_b
    target: merge
```

Both `source_a` and `source_b` execute before `merge`.

---

## Comparison

| Flow Type | Behavior | Use Case |
|-----------|----------|----------|
| `sequential` | All matching steps run | Data pipelines, multi-step processing |
| `conditional` | First match wins, then stop | Request routing, dispatch, switch/case |
| `graph` | DAG with port-based routing | Agent orchestration, approval flows, complex workflows |

---

## Step Configuration (Sequential/Conditional)

Each step can have the following options:

```yaml
steps:
  - component: my_component      # Required: component name
    description: "What it does"  # Optional: documentation
    condition: "expression"      # Optional: when to run
    on_error: fail               # Optional: error handling
```

### Component (Required)

References a component defined in the `components` section:

```yaml
components:
  - name: processor
    type: myapp.ProcessorComponent

flow:
  steps:
    - component: processor  # Must match component name
```

### Description (Optional)

Documents what the step does:

```yaml
steps:
  - component: validate
    description: "Validate input data against schema"
```

### Condition (Optional)

A Python expression evaluated at runtime. See [Conditions](conditions.md) for full details.

```yaml
steps:
  - component: send_notification
    condition: "context.data.should_notify == True"
```

### On Error (Optional)

How to handle errors in this step:

| Value | Behavior |
|-------|----------|
| `fail` | Stop execution, raise exception (default) |
| `skip` | Log error, mark step as skipped |
| `continue` | Log error, continue to next step |

```yaml
steps:
  - component: optional_step
    on_error: continue

  - component: critical_step
    on_error: fail
```

---

## Flow Settings

Configure execution behavior:

```yaml
flow:
  settings:
    fail_fast: true
    timeout_seconds: 300
    timeout_mode: cooperative
    require_deadline_check: false
    on_condition_error: fail
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `fail_fast` | `true` | Stop on first component error |
| `timeout_seconds` | `300` | Maximum execution time in seconds |
| `timeout_mode` | `cooperative` | `cooperative`, `hard_async`, or `hard_process` |
| `require_deadline_check` | `false` | Require components to call `check_deadline()` |
| `on_condition_error` | `fail` | `fail`, `skip`, or `warn` |

---

## Complete Examples

### Data Pipeline (Sequential)

```yaml
name: "ETL Pipeline"
version: "2.0"

components:
  - name: extract
    type: etl.ExtractComponent
    config:
      source: "database"

  - name: transform
    type: etl.TransformComponent
    config:
      operations: ["clean", "normalize"]

  - name: validate
    type: etl.ValidateComponent

  - name: load
    type: etl.LoadComponent
    config:
      destination: "warehouse"

  - name: notify_success
    type: etl.NotifyComponent
    config:
      channel: "slack"

  - name: notify_failure
    type: etl.NotifyComponent
    config:
      channel: "pagerduty"

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 3600

  steps:
    - component: extract
      description: "Extract data from source"

    - component: transform
      description: "Apply transformations"
      condition: "context.data.extract_status == 'success'"
      on_error: continue

    - component: validate
      description: "Validate transformed data"
      condition: "context.data.transformed_data is not None"

    - component: load
      description: "Load into data warehouse"
      condition: "context.data.validation_passed == True"

    - component: notify_success
      condition: "context.data.load_status == 'success'"

    - component: notify_failure
      condition: "context.metadata.has_errors == True"
```

### Request Router (Conditional)

```yaml
name: "API Request Router"
version: "1.0"

components:
  - name: auth_check
    type: api.AuthComponent

  - name: handle_users
    type: api.UserHandler

  - name: handle_orders
    type: api.OrderHandler

  - name: handle_products
    type: api.ProductHandler

  - name: handle_admin
    type: api.AdminHandler

  - name: handle_not_found
    type: api.NotFoundHandler

flow:
  type: sequential
  steps:
    # Auth always runs first
    - component: auth_check
      description: "Verify authentication"

# Then route based on request
flow:
  type: conditional
  steps:
    - component: handle_admin
      condition: "context.data.user.is_admin == True and context.data.path.startswith('/admin')"

    - component: handle_users
      condition: "context.data.path.startswith('/users')"

    - component: handle_orders
      condition: "context.data.path.startswith('/orders')"

    - component: handle_products
      condition: "context.data.path.startswith('/products')"

    - component: handle_not_found
      # No condition = default case
```

### Approval Workflow (Graph with Suspend/Resume)

```yaml
name: "Approval Workflow"
version: "1.0"

components:
  - name: intake
    type: workflow.IntakeComponent
  - name: approval
    type: workflow.ApprovalComponent
  - name: process_approved
    type: workflow.ProcessComponent
  - name: process_rejected
    type: workflow.RejectionComponent

flow:
  type: graph
  settings:
    timeout_seconds: 3600
  nodes:
    - id: intake
      component: intake
    - id: approve
      component: approval
    - id: approved
      component: process_approved
    - id: rejected
      component: process_rejected
  edges:
    - source: intake
      target: approve
    - source: approve
      target: approved
      port: "approved"
    - source: approve
      target: rejected
      port: "rejected"
```

---

## Dry Run

Preview which steps would execute without running them:

```python
engine = FlowEngine(config, components)
context = FlowContext()
context.set("request_type", "order")

# Preview execution
steps_to_run = engine.dry_run(context)
print("Would execute:", steps_to_run)
# Output: ["handle_order"]
```

---

## Next Steps

- [Conditions](conditions.md) - Master condition expressions
- [Timeout Modes](timeout-modes.md) - Protect against runaway flows
- [Error Handling](error-handling.md) - Handle failures gracefully
