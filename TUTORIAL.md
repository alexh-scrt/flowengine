# FlowEngine Developer Tutorial

**A comprehensive guide to building dynamic, flexible applications with FlowEngine**

---

## Table of Contents

- [Part 1: Getting Started](#part-1-getting-started)
  - [1.1 Introduction to FlowEngine](#11-introduction-to-flowengine)
  - [1.2 Your First Flow](#12-your-first-flow)
  - [1.3 Understanding the Component Lifecycle](#13-understanding-the-component-lifecycle)
  - [Exercise 1: Build Your Own Flow](#exercise-1-build-your-own-flow)
- [Part 2: Flow Configuration Deep Dive](#part-2-flow-configuration-deep-dive)
  - [2.1 YAML Configuration Reference](#21-yaml-configuration-reference)
  - [2.2 Flow Types: Sequential vs Conditional](#22-flow-types-sequential-vs-conditional)
  - [2.3 Condition Expressions](#23-condition-expressions)
  - [Exercise 2: Multi-Branch Routing](#exercise-2-multi-branch-routing)
- [Part 3: Data Flow & Context](#part-3-data-flow--context)
  - [3.1 Working with FlowContext](#31-working-with-flowcontext)
  - [3.2 Execution Metadata](#32-execution-metadata)
  - [Exercise 3: Data Aggregation Component](#exercise-3-data-aggregation-component)
- [Part 4: Error Handling & Resilience](#part-4-error-handling--resilience)
  - [4.1 Error Handling Strategies](#41-error-handling-strategies)
  - [4.2 Timeout Management](#42-timeout-management)
  - [Exercise 4: Resilient File Processing](#exercise-4-resilient-file-processing)
- [Part 5: Advanced Patterns](#part-5-advanced-patterns)
  - [5.1 Component Registry & Auto-Loading](#51-component-registry--auto-loading)
  - [5.2 Building Reusable Components](#52-building-reusable-components)
  - [5.3 Real-World Patterns](#53-real-world-patterns)
  - [Exercise 5: Full ETL Pipeline](#exercise-5-full-etl-pipeline)
- [Part 6: Built-in Components](#part-6-built-in-components)
  - [6.1 LoggingComponent](#61-loggingcomponent)
  - [6.2 HTTPComponent](#62-httpcomponent)
- [Part 7: Testing & Debugging](#part-7-testing--debugging)
  - [7.1 Unit Testing Components](#71-unit-testing-components)
  - [7.2 Integration Testing Flows](#72-integration-testing-flows)
  - [7.3 Debugging with Dry-Run and Metadata](#73-debugging-with-dry-run-and-metadata)
- [Appendix A: Complete YAML Examples](#appendix-a-complete-yaml-examples)
- [Appendix B: Common Patterns Cheat Sheet](#appendix-b-common-patterns-cheat-sheet)
- [Appendix C: Troubleshooting Guide](#appendix-c-troubleshooting-guide)

---

# Part 1: Getting Started

## 1.1 Introduction to FlowEngine

### What is FlowEngine?

FlowEngine is a lightweight, YAML-driven state machine for Python that enables developers to:

- **Define execution flows declaratively** in human-readable YAML files
- **Build pluggable component systems** with standardized interfaces
- **Execute conditional branching** based on runtime state
- **Track execution metadata** including timing, errors, and skipped steps

### Why Use FlowEngine?

| Challenge | FlowEngine Solution |
|-----------|---------------------|
| Complex orchestration logic scattered across code | Declarative YAML configuration |
| Tightly coupled components | Standardized component interface |
| Difficult to modify execution flow | Change YAML without touching code |
| No visibility into execution | Rich metadata tracking |
| Hard to handle errors gracefully | Configurable error handling per step |
| Runaway processes | Multiple timeout enforcement modes |

### Core Concepts

```
┌─────────────────────────────────────────────────────────────────┐
│                         FlowEngine                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  Component A │───►│  Component B │───►│  Component C │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         └───────────────────┴───────────────────┘               │
│                             │                                    │
│                      ┌──────▼──────┐                            │
│                      │ FlowContext │                            │
│                      │  (shared    │                            │
│                      │   state)    │                            │
│                      └─────────────┘                            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Key Components:**
- **Components**: Reusable processing units with a standardized lifecycle
- **FlowContext**: Shared state that flows through all components
- **FlowEngine**: Orchestrator that executes components according to YAML configuration
- **Conditions**: Python expressions that control step execution

### Installation

```bash
# Basic installation
pip install flowengine

# With HTTP component support
pip install flowengine[http]

# For development
pip install flowengine[dev]
```

---

## 1.2 Your First Flow

Let's build a simple flow that greets a user and converts the message to uppercase.

### Step 1: Create Your Components

```python
# my_components.py
from flowengine import BaseComponent, FlowContext


class GreetComponent(BaseComponent):
    """Component that generates a greeting message."""

    def init(self, config: dict) -> None:
        """Called once when flow is set up."""
        super().init(config)
        self.greeting = config.get("greeting", "Hello")

    def process(self, context: FlowContext) -> FlowContext:
        """Main processing logic - called each execution."""
        name = context.get("name", "World")
        message = f"{self.greeting}, {name}!"
        context.set("message", message)
        print(f"  [GreetComponent] Generated: {message}")
        return context


class ShoutComponent(BaseComponent):
    """Component that converts message to uppercase."""

    def process(self, context: FlowContext) -> FlowContext:
        message = context.get("message", "")
        shouted = message.upper()
        context.set("shouted", shouted)
        print(f"  [ShoutComponent] Converted to: {shouted}")
        return context
```

### Step 2: Create the YAML Configuration

```yaml
# greeting_flow.yaml
name: "Greeting Flow"
version: "1.0"
description: "A simple flow that greets and shouts"

components:
  - name: greeter
    type: my_components.GreetComponent
    config:
      greeting: "Hello"

  - name: shouter
    type: my_components.ShoutComponent
    config: {}

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 30
  steps:
    - component: greeter
      description: "Generate a greeting message"
    - component: shouter
      description: "Convert message to uppercase"
```

### Step 3: Execute the Flow

```python
# run_flow.py
from flowengine import ConfigLoader, FlowContext, FlowEngine
from my_components import GreetComponent, ShoutComponent


def main():
    # Load configuration from YAML
    config = ConfigLoader.load("greeting_flow.yaml")
    print(f"Loaded flow: {config.name}")

    # Create component instances
    components = {
        "greeter": GreetComponent("greeter"),
        "shouter": ShoutComponent("shouter"),
    }

    # Create engine
    engine = FlowEngine(config, components)

    # Validate the flow
    errors = engine.validate()
    if errors:
        print(f"Validation errors: {errors}")
        return

    # Execute the flow
    print("\n--- Executing Flow ---")
    context = FlowContext()
    context.set("name", "FlowEngine User")

    result = engine.execute(context)

    # Show results
    print("\n--- Results ---")
    print(f"Message: {result.data.message}")
    print(f"Shouted: {result.data.shouted}")
    print(f"Execution time: {result.metadata.total_duration:.4f}s")


if __name__ == "__main__":
    main()
```

**Output:**
```
Loaded flow: Greeting Flow

--- Executing Flow ---
  [GreetComponent] Generated: Hello, FlowEngine User!
  [ShoutComponent] Converted to: HELLO, FLOWENGINE USER!

--- Results ---
Message: Hello, FlowEngine User!
Shouted: HELLO, FLOWENGINE USER!
Execution time: 0.0012s
```

### Understanding the Execution Flow

1. **Load Configuration**: `ConfigLoader.load()` parses YAML and validates schema
2. **Create Components**: Instantiate component classes with names matching YAML
3. **Create Engine**: `FlowEngine` binds configuration to components
4. **Validate**: Check all components exist and configurations are valid
5. **Execute**: Run each step in order, passing context through
6. **Access Results**: Read data and metadata from returned context

---

## 1.3 Understanding the Component Lifecycle

Every component follows a structured lifecycle:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Component Lifecycle                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. __init__(name)     ─── Instance creation                    │
│         │                                                        │
│         ▼                                                        │
│  2. init(config)       ─── One-time configuration (once)        │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  For each execution:                                     │    │
│  │                                                          │    │
│  │  3. setup(context)   ─── Pre-processing preparation     │    │
│  │         │                                                │    │
│  │         ▼                                                │    │
│  │  4. process(context) ─── Main logic [REQUIRED]          │    │
│  │         │                                                │    │
│  │         ▼                                                │    │
│  │  5. teardown(context) ─── Cleanup (always runs)         │    │
│  │                                                          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Lifecycle Methods Explained

| Method | When Called | Purpose | Required? |
|--------|-------------|---------|-----------|
| `__init__(name)` | Instance creation | Store component name | Yes (inherited) |
| `init(config)` | Once, during flow setup | Load config, create clients | No |
| `setup(context)` | Before each `process()` | Open connections, temp state | No |
| `process(context)` | Each execution | Main business logic | **Yes** |
| `teardown(context)` | After `process()` | Cleanup, close connections | No |
| `validate_config()` | During validation | Check required config | No |
| `health_check()` | On demand | Verify component health | No |

### Example: Database Component with Full Lifecycle

```python
from flowengine import BaseComponent, FlowContext


class DatabaseComponent(BaseComponent):
    """Component demonstrating full lifecycle with resource management."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._connection = None

    def init(self, config: dict) -> None:
        """Called once - store configuration."""
        super().init(config)
        self.connection_string = config.get("connection_string", "")
        self.table_name = config.get("table_name", "")

    def validate_config(self) -> list[str]:
        """Validate required configuration keys."""
        errors = []
        if not self.connection_string:
            errors.append("connection_string is required")
        if not self.table_name:
            errors.append("table_name is required")
        return errors

    def setup(self, context: FlowContext) -> None:
        """Called before each process() - open connection."""
        print(f"  [{self.name}] Opening database connection...")
        # In real code: self._connection = create_connection(self.connection_string)
        self._connection = {"connected": True, "table": self.table_name}

    def process(self, context: FlowContext) -> FlowContext:
        """Main logic - query database."""
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Simulate query
        result = {
            "table": self.table_name,
            "rows": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "count": 2,
        }
        context.set("db_result", result)
        print(f"  [{self.name}] Queried {result['count']} rows from {self.table_name}")
        return context

    def teardown(self, context: FlowContext) -> None:
        """Called after process() - close connection (even if process failed)."""
        if self._connection:
            print(f"  [{self.name}] Closing database connection...")
            self._connection = None

    def health_check(self) -> bool:
        """Check if component is ready."""
        return self.is_initialized and bool(self.connection_string)
```

### Key Points

1. **`teardown()` Always Runs**: Even if `process()` raises an exception, `teardown()` is called
2. **Configuration Validation**: Use `validate_config()` to catch missing/invalid config early
3. **Resource Management**: Open resources in `setup()`, close in `teardown()`
4. **Stateless Processing**: Don't store execution state in instance variables between runs

---

## Exercise 1: Build Your Own Flow

### Challenge

Create a flow that processes a user order:

1. **ValidateOrderComponent**: Check that order has required fields (customer_id, items)
2. **CalculateTotalComponent**: Sum up item prices
3. **ApplyDiscountComponent**: Apply 10% discount if total > $100

### Requirements

- Create three components
- Write YAML configuration
- Execute and verify results

### Solution

<details>
<summary>Click to reveal solution</summary>

**Components (order_components.py):**

```python
from flowengine import BaseComponent, FlowContext


class ValidateOrderComponent(BaseComponent):
    """Validates order has required fields."""

    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", {})

        errors = []
        if not order.get("customer_id"):
            errors.append("customer_id is required")
        if not order.get("items"):
            errors.append("items list is required")

        context.set("validation", {
            "valid": len(errors) == 0,
            "errors": errors,
        })

        if errors:
            print(f"  [Validate] Validation failed: {errors}")
        else:
            print(f"  [Validate] Order is valid")

        return context


class CalculateTotalComponent(BaseComponent):
    """Calculates order total from items."""

    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", {})
        items = order.get("items", [])

        total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)

        context.set("subtotal", total)
        print(f"  [Calculate] Subtotal: ${total:.2f}")

        return context


class ApplyDiscountComponent(BaseComponent):
    """Applies discount if total exceeds threshold."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.threshold = config.get("threshold", 100)
        self.discount_percent = config.get("discount_percent", 10)

    def process(self, context: FlowContext) -> FlowContext:
        subtotal = context.get("subtotal", 0)

        if subtotal > self.threshold:
            discount = subtotal * (self.discount_percent / 100)
            final_total = subtotal - discount
            print(f"  [Discount] Applied {self.discount_percent}% discount: -${discount:.2f}")
        else:
            discount = 0
            final_total = subtotal
            print(f"  [Discount] No discount (subtotal <= ${self.threshold})")

        context.set("discount", discount)
        context.set("final_total", final_total)

        return context
```

**YAML Configuration (order_flow.yaml):**

```yaml
name: "Order Processing Flow"
version: "1.0"
description: "Validates, calculates, and applies discounts to orders"

components:
  - name: validator
    type: order_components.ValidateOrderComponent
    config: {}

  - name: calculator
    type: order_components.CalculateTotalComponent
    config: {}

  - name: discounter
    type: order_components.ApplyDiscountComponent
    config:
      threshold: 100
      discount_percent: 10

flow:
  type: sequential
  settings:
    fail_fast: true
  steps:
    - component: validator
      description: "Validate order fields"

    - component: calculator
      description: "Calculate subtotal"
      condition: "context.data.validation.valid == True"

    - component: discounter
      description: "Apply discount if eligible"
      condition: "context.data.subtotal is not None"
```

**Execution (run_order.py):**

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine
from order_components import (
    ValidateOrderComponent,
    CalculateTotalComponent,
    ApplyDiscountComponent,
)


def main():
    config = ConfigLoader.load("order_flow.yaml")

    components = {
        "validator": ValidateOrderComponent("validator"),
        "calculator": CalculateTotalComponent("calculator"),
        "discounter": ApplyDiscountComponent("discounter"),
    }

    engine = FlowEngine(config, components)

    # Test order
    context = FlowContext()
    context.set("order", {
        "customer_id": "CUST-001",
        "items": [
            {"name": "Widget", "price": 25.00, "quantity": 3},
            {"name": "Gadget", "price": 50.00, "quantity": 1},
        ],
    })

    result = engine.execute(context)

    print("\n--- Order Summary ---")
    print(f"Subtotal: ${result.data.subtotal:.2f}")
    print(f"Discount: ${result.data.discount:.2f}")
    print(f"Final Total: ${result.data.final_total:.2f}")


if __name__ == "__main__":
    main()
```

**Output:**
```
  [Validate] Order is valid
  [Calculate] Subtotal: $125.00
  [Discount] Applied 10% discount: -$12.50

--- Order Summary ---
Subtotal: $125.00
Discount: $12.50
Final Total: $112.50
```

</details>

---

# Part 2: Flow Configuration Deep Dive

## 2.1 YAML Configuration Reference

### Complete Configuration Structure

```yaml
# Root configuration
name: "Flow Name"                    # Required: Human-readable name
version: "1.0"                       # Optional: Configuration version
description: "Flow description"      # Optional: What this flow does

# Component definitions
components:                          # Required: List of components
  - name: component_name             # Required: Unique identifier
    type: module.path.ClassName      # Required: Python class path
    config:                          # Optional: Component-specific config
      key: value

# Flow definition
flow:                                # Required: Flow structure
  type: sequential                   # Optional: "sequential" (default) or "conditional"

  settings:                          # Optional: Execution settings
    fail_fast: true                  # Stop on first error (default: true)
    timeout_seconds: 300             # Max execution time (default: 300)
    timeout_mode: cooperative        # cooperative|hard_async|hard_process
    require_deadline_check: false    # Enforce deadline checks (default: false)
    on_condition_error: fail         # fail|skip|warn (default: fail)

  steps:                             # Required: Ordered execution steps
    - component: component_name      # Required: Component to execute
      description: "Step description" # Optional: Human-readable description
      condition: "expression"        # Optional: Python expression
      on_error: fail                 # Optional: fail|skip|continue
```

### Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `fail_fast` | boolean | `true` | Stop flow on first component error |
| `timeout_seconds` | float | `300` | Maximum flow execution time in seconds |
| `timeout_mode` | string | `cooperative` | Timeout enforcement mode |
| `require_deadline_check` | boolean | `false` | Require components to call `check_deadline()` |
| `on_condition_error` | string | `fail` | How to handle invalid condition expressions |

### Step Configuration

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `component` | string | Yes | Name of component to execute |
| `description` | string | No | Human-readable step description |
| `condition` | string | No | Python expression for conditional execution |
| `on_error` | string | No | Error handling: `fail`, `skip`, `continue` |

---

## 2.2 Flow Types: Sequential vs Conditional

FlowEngine supports two distinct flow execution patterns:

### Sequential Flow (Default)

**Behavior**: Executes ALL steps in order. Each step's condition guards whether THAT step runs.

```yaml
flow:
  type: sequential  # All matching steps execute

  steps:
    - component: fetch_data      # Always runs (no condition)

    - component: transform_data  # Runs if fetch succeeded
      condition: "context.data.fetch_result.status == 'success'"

    - component: save_data       # Runs if transformed data exists
      condition: "context.data.transformed is not None"

    - component: notify_error    # Runs if fetch failed
      condition: "context.data.fetch_result.status == 'error'"
```

**Execution Pattern:**
```
Step 1: fetch_data      → EXECUTED
Step 2: transform_data  → condition True? → EXECUTED or SKIPPED
Step 3: save_data       → condition True? → EXECUTED or SKIPPED
Step 4: notify_error    → condition True? → EXECUTED or SKIPPED
```

**Use Cases:**
- Data pipelines
- Multi-step processing
- Parallel conditional branches (multiple steps can match)

### Conditional Flow (First-Match Branching)

**Behavior**: Stops after FIRST step whose condition evaluates to True. Like `switch/case` or `if/elif/else`.

```yaml
flow:
  type: conditional  # First match wins, then stop

  steps:
    - component: handle_user
      condition: "context.data.request_type == 'user'"

    - component: handle_order
      condition: "context.data.request_type == 'order'"

    - component: handle_admin
      condition: "context.data.request_type == 'admin'"

    - component: handle_unknown  # No condition = default case
```

**Execution Pattern:**
```
Check Step 1: handle_user  → condition True? → EXECUTE & STOP
Check Step 2: handle_order → condition True? → EXECUTE & STOP
Check Step 3: handle_admin → condition True? → EXECUTE & STOP
Check Step 4: handle_unknown → (no condition) → EXECUTE & STOP
```

**Use Cases:**
- Request routing
- Dispatch systems
- Mutually exclusive branches

### Comparison Table

| Aspect | Sequential | Conditional |
|--------|-----------|-------------|
| Steps executed | All matching | First matching only |
| Default `on_condition_error` | `fail` | `skip` |
| Use case | Pipelines | Routing/Dispatch |
| Condition semantics | Guard each step | Match for branching |
| Multiple matches | All run | Only first runs |

### Visual Comparison

```
Sequential Flow:                    Conditional Flow:

    ┌──────┐                           ┌──────┐
    │ Step │                           │ Step │
    │  1   │                           │  1   │──── Match? ──► STOP
    └──┬───┘                           └──┬───┘
       │                                  │ No
       ▼                                  ▼
    ┌──────┐                           ┌──────┐
    │ Step │── Condition?              │ Step │
    │  2   │── True: RUN               │  2   │──── Match? ──► STOP
    └──┬───┘── False: SKIP             └──┬───┘
       │                                  │ No
       ▼                                  ▼
    ┌──────┐                           ┌──────┐
    │ Step │── Condition?              │ Step │
    │  3   │── True: RUN               │  3   │──── Match? ──► STOP
    └──┬───┘── False: SKIP             └──────┘
       │
       ▼                               (Only ONE step executes)
    Continue to all steps...
```

---

## 2.3 Condition Expressions

### Safe Expression Syntax

FlowEngine uses AST (Abstract Syntax Tree) validation to ensure conditions are safe:

```python
# Conditions are Python expressions evaluated against context
"context.data.user.active == True"
"context.data.count > 5"
"context.data.status in ['pending', 'approved']"
```

### Allowed Operations

| Category | Operators | Examples |
|----------|-----------|----------|
| **Comparisons** | `==`, `!=`, `<`, `<=`, `>`, `>=` | `context.data.age >= 18` |
| **Boolean** | `and`, `or`, `not` | `context.data.a and context.data.b` |
| **Identity** | `is`, `is not` | `context.data.value is not None` |
| **Membership** | `in`, `not in` | `context.data.status in ['a', 'b']` |
| **Arithmetic** | `+`, `-`, `*`, `/`, `%`, `//` | `context.data.x + context.data.y > 10` |
| **Attributes** | `.` | `context.data.user.profile.name` |
| **Subscripts** | `[]` | `context.data.items[0]` |

### Accessing Context Data

```python
# Direct attribute access
"context.data.user_id"

# Nested access
"context.data.user.profile.settings.theme"

# Dictionary-style access
"context.data.items[0]"
"context.data.config['api_key']"

# Input data access
"context.input.request_type"

# Combined conditions
"context.data.user.active and context.data.user.age >= 18"
```

### Disallowed for Security

| Category | Example | Why Blocked |
|----------|---------|-------------|
| Function calls | `len(context.data.items)` | Could execute arbitrary code |
| Method calls | `context.data.name.upper()` | Could have side effects |
| Lambda expressions | `lambda x: x > 5` | Code injection risk |
| Comprehensions | `[x for x in items]` | Arbitrary iteration |
| Imports | `import os` | System access |
| Assignments | `x = 5` | State modification |

### Valid Condition Examples

```yaml
# Simple comparisons
condition: "context.data.status == 'active'"
condition: "context.data.count > 0"
condition: "context.data.amount >= 100.0"

# Boolean logic
condition: "context.data.enabled and context.data.verified"
condition: "context.data.role == 'admin' or context.data.role == 'superuser'"
condition: "not context.data.blocked"

# Null checks
condition: "context.data.result is not None"
condition: "context.data.error is None"

# Membership tests
condition: "context.data.status in ['pending', 'approved', 'active']"
condition: "context.data.user_type not in ['banned', 'suspended']"

# Nested access
condition: "context.data.response.data.items[0].status == 'ready'"

# Complex conditions
condition: |
  context.data.user.active and
  context.data.user.email_verified and
  context.data.subscription.status == 'active'
```

### Condition Error Handling

When a condition fails to evaluate (syntax error, missing attribute, etc.):

```yaml
flow:
  settings:
    on_condition_error: fail   # Raise ConditionEvaluationError (default)
    # on_condition_error: skip # Skip the step, record error
    # on_condition_error: warn # Log warning, skip the step
```

---

## Exercise 2: Multi-Branch Routing

### Challenge

Create a request router that dispatches API requests to different handlers:

1. **GET /users** → UserListHandler
2. **GET /users/:id** → UserDetailHandler
3. **POST /users** → UserCreateHandler
4. **DELETE /users/:id** → UserDeleteHandler
5. **Unknown** → NotFoundHandler

### Requirements

- Use conditional flow type
- Parse method and path from request
- Each handler sets appropriate response

### Solution

<details>
<summary>Click to reveal solution</summary>

**Components (router_components.py):**

```python
from flowengine import BaseComponent, FlowContext
import re


class RequestParserComponent(BaseComponent):
    """Parses incoming request into method and path pattern."""

    def process(self, context: FlowContext) -> FlowContext:
        request = context.get("request", {})
        method = request.get("method", "GET").upper()
        path = request.get("path", "/")

        # Determine route pattern
        if re.match(r"^/users/\d+$", path):
            pattern = "/users/:id"
            user_id = path.split("/")[-1]
            context.set("user_id", user_id)
        elif path == "/users":
            pattern = "/users"
        else:
            pattern = "unknown"

        context.set("route", {
            "method": method,
            "path": path,
            "pattern": pattern,
        })

        print(f"  [Parser] {method} {path} -> pattern: {pattern}")
        return context


class UserListHandler(BaseComponent):
    """Handles GET /users"""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("response", {
            "status": 200,
            "data": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
            ],
        })
        print("  [UserList] Returning user list")
        return context


class UserDetailHandler(BaseComponent):
    """Handles GET /users/:id"""

    def process(self, context: FlowContext) -> FlowContext:
        user_id = context.get("user_id")
        context.set("response", {
            "status": 200,
            "data": {"id": int(user_id), "name": f"User {user_id}"},
        })
        print(f"  [UserDetail] Returning user {user_id}")
        return context


class UserCreateHandler(BaseComponent):
    """Handles POST /users"""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("response", {
            "status": 201,
            "data": {"id": 3, "name": "New User", "created": True},
        })
        print("  [UserCreate] Created new user")
        return context


class UserDeleteHandler(BaseComponent):
    """Handles DELETE /users/:id"""

    def process(self, context: FlowContext) -> FlowContext:
        user_id = context.get("user_id")
        context.set("response", {
            "status": 204,
            "data": None,
        })
        print(f"  [UserDelete] Deleted user {user_id}")
        return context


class NotFoundHandler(BaseComponent):
    """Handles unknown routes"""

    def process(self, context: FlowContext) -> FlowContext:
        route = context.get("route", {})
        context.set("response", {
            "status": 404,
            "error": f"Route not found: {route.get('method')} {route.get('path')}",
        })
        print("  [NotFound] Route not found")
        return context
```

**YAML Configuration (router_flow.yaml):**

```yaml
name: "API Request Router"
version: "1.0"
description: "Routes API requests to appropriate handlers"

components:
  - name: parser
    type: router_components.RequestParserComponent
    config: {}

  - name: user_list
    type: router_components.UserListHandler
    config: {}

  - name: user_detail
    type: router_components.UserDetailHandler
    config: {}

  - name: user_create
    type: router_components.UserCreateHandler
    config: {}

  - name: user_delete
    type: router_components.UserDeleteHandler
    config: {}

  - name: not_found
    type: router_components.NotFoundHandler
    config: {}

flow:
  type: sequential  # Parser must run first
  settings:
    fail_fast: true
  steps:
    # First, parse the request
    - component: parser
      description: "Parse incoming request"

---
# Second flow: Route to handler (conditional)
name: "Request Handler Router"

flow:
  type: conditional  # First match wins
  steps:
    - component: user_list
      description: "Handle GET /users"
      condition: |
        context.data.route.method == 'GET' and
        context.data.route.pattern == '/users'

    - component: user_detail
      description: "Handle GET /users/:id"
      condition: |
        context.data.route.method == 'GET' and
        context.data.route.pattern == '/users/:id'

    - component: user_create
      description: "Handle POST /users"
      condition: |
        context.data.route.method == 'POST' and
        context.data.route.pattern == '/users'

    - component: user_delete
      description: "Handle DELETE /users/:id"
      condition: |
        context.data.route.method == 'DELETE' and
        context.data.route.pattern == '/users/:id'

    - component: not_found
      description: "Handle unknown routes"
      # No condition = default fallback
```

**Simpler Single Flow Approach (router_flow_simple.yaml):**

```yaml
name: "API Request Router"
version: "1.0"

components:
  - name: parser
    type: router_components.RequestParserComponent
  - name: user_list
    type: router_components.UserListHandler
  - name: user_detail
    type: router_components.UserDetailHandler
  - name: user_create
    type: router_components.UserCreateHandler
  - name: user_delete
    type: router_components.UserDeleteHandler
  - name: not_found
    type: router_components.NotFoundHandler

flow:
  type: sequential
  steps:
    # Parse request first (always runs)
    - component: parser

    # Then route conditionally (only one should match)
    - component: user_list
      condition: "context.data.route.method == 'GET' and context.data.route.pattern == '/users'"

    - component: user_detail
      condition: "context.data.route.method == 'GET' and context.data.route.pattern == '/users/:id'"

    - component: user_create
      condition: "context.data.route.method == 'POST' and context.data.route.pattern == '/users'"

    - component: user_delete
      condition: "context.data.route.method == 'DELETE' and context.data.route.pattern == '/users/:id'"

    - component: not_found
      condition: "context.data.response is None"
```

**Execution:**

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine
from router_components import *


def test_route(method: str, path: str):
    config = ConfigLoader.load("router_flow_simple.yaml")

    components = {
        "parser": RequestParserComponent("parser"),
        "user_list": UserListHandler("user_list"),
        "user_detail": UserDetailHandler("user_detail"),
        "user_create": UserCreateHandler("user_create"),
        "user_delete": UserDeleteHandler("user_delete"),
        "not_found": NotFoundHandler("not_found"),
    }

    engine = FlowEngine(config, components)

    context = FlowContext()
    context.set("request", {"method": method, "path": path})

    result = engine.execute(context)

    response = result.get("response", {})
    print(f"\nResponse: {response}")
    return response


# Test cases
print("=== GET /users ===")
test_route("GET", "/users")

print("\n=== GET /users/123 ===")
test_route("GET", "/users/123")

print("\n=== POST /users ===")
test_route("POST", "/users")

print("\n=== DELETE /users/456 ===")
test_route("DELETE", "/users/456")

print("\n=== GET /unknown ===")
test_route("GET", "/unknown")
```

</details>

---

# Part 3: Data Flow & Context

## 3.1 Working with FlowContext

The `FlowContext` is the shared state container that flows through all components:

```python
from flowengine import FlowContext

# Create a new context
context = FlowContext()
```

### Setting and Getting Data

```python
# Set values
context.set("user_id", 123)
context.set("user", {"name": "Alice", "email": "alice@example.com"})
context.set("items", [1, 2, 3, 4, 5])

# Get values
user_id = context.get("user_id")           # 123
user_name = context.get("user_name", "Unknown")  # "Unknown" (default)

# Check existence
if context.has("user"):
    print("User exists")

# Delete values
context.delete("temporary_data")
```

### DotDict: Attribute-Style Access

Context data is stored in a `DotDict` that allows attribute-style access:

```python
context.set("user", {
    "name": "Alice",
    "profile": {
        "age": 30,
        "settings": {
            "theme": "dark",
            "notifications": True,
        }
    }
})

# Attribute-style access (dot notation)
print(context.data.user.name)                    # "Alice"
print(context.data.user.profile.age)             # 30
print(context.data.user.profile.settings.theme)  # "dark"

# Still works with bracket notation
print(context.data["user"]["name"])              # "Alice"

# Missing keys return None (no KeyError)
print(context.data.user.nonexistent)             # None
```

### Input Data

Pass initial data when executing:

```python
# Option 1: Set on context before execution
context = FlowContext()
context.set("initial_value", 100)
result = engine.execute(context)

# Option 2: Pass as input_data parameter
result = engine.execute(input_data={"request_id": "abc-123"})

# Access input in components
class MyComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        request_id = context.input.request_id  # or context.input["request_id"]
        return context
```

### Context Serialization

Save and restore context state:

```python
# After execution
result = engine.execute(context)

# Serialize to dictionary
context_dict = result.to_dict()

# Serialize to JSON string
json_str = result.to_json(indent=2)

# Save to file
with open("context_snapshot.json", "w") as f:
    f.write(json_str)

# Later, restore the context
with open("context_snapshot.json", "r") as f:
    restored = FlowContext.from_json(f.read())

# All data and metadata preserved
print(restored.data.user.name)
print(restored.metadata.flow_id)
print(restored.metadata.step_timings)

# Create a copy
context_copy = context.copy()
```

---

## 3.2 Execution Metadata

Every execution tracks detailed metadata:

```python
result = engine.execute(context)
metadata = result.metadata
```

### Flow Identification

```python
# Unique flow execution ID
print(metadata.flow_id)        # "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Timestamps
print(metadata.started_at)     # datetime object
print(metadata.completed_at)   # datetime object (set when done)
print(metadata.total_duration) # Total seconds (float)
```

### Step Timings

```python
# Individual step timings (preserves order)
for step in metadata.step_timings:
    print(f"Step {step.step_index}: {step.component}")
    print(f"  Duration: {step.duration:.3f}s")
    print(f"  Started: {step.started_at}")
    print(f"  Execution order: {step.execution_order}")

# Aggregated by component (backward-compatible)
for component, total_time in metadata.component_timings.items():
    print(f"{component}: {total_time:.3f}s total")
```

### Skipped Components

```python
# Components skipped due to conditions
print(metadata.skipped_components)  # ["step2", "step4"]

# Check in conditions
if "error_handler" in metadata.skipped_components:
    print("No errors occurred")
```

### Error Tracking

```python
# Check for errors
if metadata.has_errors:
    for error in metadata.errors:
        print(f"Component: {error['component']}")
        print(f"Error type: {error['error_type']}")
        print(f"Message: {error['message']}")
        print(f"Timestamp: {error['timestamp']}")

# Condition evaluation errors
if metadata.has_condition_errors:
    for error in metadata.condition_errors:
        print(f"Component: {error['component']}")
        print(f"Condition: {error['condition']}")
        print(f"Error: {error['message']}")
```

### Complete Metadata Example

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine


def analyze_execution(result):
    """Analyze flow execution results."""
    m = result.metadata

    print(f"\n{'='*50}")
    print(f"Flow Execution Report")
    print(f"{'='*50}")
    print(f"Flow ID: {m.flow_id}")
    print(f"Duration: {m.total_duration:.3f}s")
    print(f"Started: {m.started_at}")
    print(f"Completed: {m.completed_at}")

    print(f"\n--- Step Execution ---")
    for step in m.step_timings:
        status = "OK"
        print(f"  [{step.step_index}] {step.component}: {step.duration:.3f}s - {status}")

    if m.skipped_components:
        print(f"\n--- Skipped Steps ---")
        for comp in m.skipped_components:
            print(f"  - {comp}")

    if m.has_errors:
        print(f"\n--- Errors ({len(m.errors)}) ---")
        for err in m.errors:
            print(f"  [{err['component']}] {err['message']}")

    if m.has_condition_errors:
        print(f"\n--- Condition Errors ({len(m.condition_errors)}) ---")
        for err in m.condition_errors:
            print(f"  [{err['component']}] {err['condition']}: {err['message']}")

    print(f"\n--- Aggregated Timings ---")
    for comp, time in m.component_timings.items():
        print(f"  {comp}: {time:.3f}s")


# Usage
result = engine.execute(context)
analyze_execution(result)
```

---

## Exercise 3: Data Aggregation Component

### Challenge

Build a statistics aggregation flow:

1. **DataLoaderComponent**: Load sample sales data
2. **FilterComponent**: Filter by date range (configurable)
3. **AggregatorComponent**: Calculate totals, averages, counts
4. **ReportComponent**: Generate summary report

Track all metadata and display execution report.

### Solution

<details>
<summary>Click to reveal solution</summary>

**Components (stats_components.py):**

```python
from flowengine import BaseComponent, FlowContext
from datetime import datetime, date


class DataLoaderComponent(BaseComponent):
    """Loads sample sales data."""

    def process(self, context: FlowContext) -> FlowContext:
        # Simulated sales data
        sales_data = [
            {"date": "2024-01-15", "product": "Widget", "amount": 150.00, "quantity": 3},
            {"date": "2024-01-20", "product": "Gadget", "amount": 250.00, "quantity": 1},
            {"date": "2024-02-05", "product": "Widget", "amount": 100.00, "quantity": 2},
            {"date": "2024-02-10", "product": "Gizmo", "amount": 75.00, "quantity": 5},
            {"date": "2024-02-15", "product": "Gadget", "amount": 500.00, "quantity": 2},
            {"date": "2024-03-01", "product": "Widget", "amount": 200.00, "quantity": 4},
            {"date": "2024-03-10", "product": "Gizmo", "amount": 150.00, "quantity": 10},
        ]

        context.set("raw_data", sales_data)
        context.set("record_count", len(sales_data))
        print(f"  [Loader] Loaded {len(sales_data)} sales records")
        return context


class FilterComponent(BaseComponent):
    """Filters data by date range."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.start_date = config.get("start_date")
        self.end_date = config.get("end_date")

    def process(self, context: FlowContext) -> FlowContext:
        raw_data = context.get("raw_data", [])
        filtered = []

        for record in raw_data:
            record_date = record["date"]
            include = True

            if self.start_date and record_date < self.start_date:
                include = False
            if self.end_date and record_date > self.end_date:
                include = False

            if include:
                filtered.append(record)

        context.set("filtered_data", filtered)
        context.set("filtered_count", len(filtered))

        print(f"  [Filter] Filtered to {len(filtered)} records")
        print(f"           Date range: {self.start_date or 'any'} to {self.end_date or 'any'}")

        return context


class AggregatorComponent(BaseComponent):
    """Calculates aggregate statistics."""

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("filtered_data", [])

        if not data:
            context.set("stats", {"error": "No data to aggregate"})
            return context

        # Calculate statistics
        total_amount = sum(r["amount"] for r in data)
        total_quantity = sum(r["quantity"] for r in data)
        avg_amount = total_amount / len(data)

        # Group by product
        by_product = {}
        for record in data:
            product = record["product"]
            if product not in by_product:
                by_product[product] = {"amount": 0, "quantity": 0, "count": 0}
            by_product[product]["amount"] += record["amount"]
            by_product[product]["quantity"] += record["quantity"]
            by_product[product]["count"] += 1

        stats = {
            "total_records": len(data),
            "total_amount": total_amount,
            "total_quantity": total_quantity,
            "average_amount": avg_amount,
            "by_product": by_product,
        }

        context.set("stats", stats)
        print(f"  [Aggregator] Calculated stats: ${total_amount:.2f} total")

        return context


class ReportComponent(BaseComponent):
    """Generates formatted report."""

    def process(self, context: FlowContext) -> FlowContext:
        stats = context.get("stats", {})
        metadata = context.metadata

        report_lines = [
            "=" * 50,
            "SALES REPORT",
            "=" * 50,
            "",
            f"Total Records: {stats.get('total_records', 0)}",
            f"Total Revenue: ${stats.get('total_amount', 0):.2f}",
            f"Total Units Sold: {stats.get('total_quantity', 0)}",
            f"Average Sale: ${stats.get('average_amount', 0):.2f}",
            "",
            "--- By Product ---",
        ]

        for product, data in stats.get("by_product", {}).items():
            report_lines.append(
                f"  {product}: ${data['amount']:.2f} "
                f"({data['quantity']} units, {data['count']} sales)"
            )

        report_lines.extend([
            "",
            "--- Execution Stats ---",
            f"Flow ID: {metadata.flow_id[:8]}...",
            f"Duration: {metadata.total_duration:.3f}s",
            "=" * 50,
        ])

        report = "\n".join(report_lines)
        context.set("report", report)
        print(f"  [Report] Generated report")

        return context
```

**YAML Configuration (stats_flow.yaml):**

```yaml
name: "Sales Statistics Flow"
version: "1.0"
description: "Loads, filters, aggregates, and reports on sales data"

components:
  - name: loader
    type: stats_components.DataLoaderComponent
    config: {}

  - name: filter
    type: stats_components.FilterComponent
    config:
      start_date: "2024-02-01"
      end_date: "2024-02-28"

  - name: aggregator
    type: stats_components.AggregatorComponent
    config: {}

  - name: reporter
    type: stats_components.ReportComponent
    config: {}

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 60
  steps:
    - component: loader
      description: "Load raw sales data"

    - component: filter
      description: "Filter by date range"
      condition: "context.data.record_count > 0"

    - component: aggregator
      description: "Calculate statistics"
      condition: "context.data.filtered_count > 0"

    - component: reporter
      description: "Generate report"
      condition: "context.data.stats is not None"
```

**Execution (run_stats.py):**

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine
from stats_components import *


def main():
    config = ConfigLoader.load("stats_flow.yaml")

    components = {
        "loader": DataLoaderComponent("loader"),
        "filter": FilterComponent("filter"),
        "aggregator": AggregatorComponent("aggregator"),
        "reporter": ReportComponent("reporter"),
    }

    engine = FlowEngine(config, components)
    result = engine.execute()

    # Print the report
    print("\n" + result.data.report)

    # Detailed metadata analysis
    print("\n--- Execution Metadata ---")
    for step in result.metadata.step_timings:
        print(f"  {step.component}: {step.duration:.4f}s")

    if result.metadata.skipped_components:
        print(f"\nSkipped: {result.metadata.skipped_components}")


if __name__ == "__main__":
    main()
```

**Output:**
```
  [Loader] Loaded 7 sales records
  [Filter] Filtered to 4 records
           Date range: 2024-02-01 to 2024-02-28
  [Aggregator] Calculated stats: $825.00 total
  [Report] Generated report

==================================================
SALES REPORT
==================================================

Total Records: 4
Total Revenue: $825.00
Total Units Sold: 10
Average Sale: $206.25

--- By Product ---
  Widget: $100.00 (2 units, 1 sales)
  Gizmo: $225.00 (15 units, 2 sales)
  Gadget: $500.00 (2 units, 1 sales)

--- Execution Stats ---
Flow ID: a1b2c3d4...
Duration: 0.003s
==================================================

--- Execution Metadata ---
  loader: 0.0001s
  filter: 0.0001s
  aggregator: 0.0002s
  reporter: 0.0001s
```

</details>

---

# Part 4: Error Handling & Resilience

## 4.1 Error Handling Strategies

FlowEngine provides multiple layers of error handling:

### Global: `fail_fast` Setting

```yaml
flow:
  settings:
    fail_fast: true   # Stop on first error (default)
    # fail_fast: false  # Continue after errors
```

When `fail_fast: true`:
- First component error stops the entire flow
- Raises `ComponentError`
- Subsequent steps are not executed

When `fail_fast: false`:
- Errors are recorded in metadata
- Flow continues to next step
- Use per-step `on_error` to control behavior

### Per-Step: `on_error` Setting

```yaml
steps:
  - component: risky_operation
    on_error: fail      # Stop flow (default)
    # on_error: skip    # Skip step, continue flow
    # on_error: continue # Ignore error, continue flow
```

| on_error | Behavior | Use Case |
|----------|----------|----------|
| `fail` | Stop flow, raise exception | Critical operations |
| `skip` | Skip step, record as skipped | Optional enhancements |
| `continue` | Ignore error, proceed | Non-critical operations |

### Condition Errors: `on_condition_error`

```yaml
flow:
  settings:
    on_condition_error: fail   # Raise ConditionEvaluationError (default)
    # on_condition_error: skip # Skip step, record error
    # on_condition_error: warn # Log warning, skip step
```

### Exception Hierarchy

```python
from flowengine import (
    FlowEngineError,        # Base exception
    ConfigurationError,     # YAML/schema errors
    FlowExecutionError,     # Runtime errors
    FlowTimeoutError,       # Timeout exceeded
    DeadlineCheckError,     # Deadline check not called
    ComponentError,         # Component processing errors
    ConditionEvaluationError,  # Invalid conditions
)
```

### Practical Error Handling

```python
from flowengine import (
    FlowEngine,
    ComponentError,
    FlowTimeoutError,
    ConditionEvaluationError,
)


def execute_with_error_handling(engine, context):
    """Execute flow with comprehensive error handling."""
    try:
        result = engine.execute(context)

        # Check for recorded errors (when fail_fast=false)
        if result.metadata.has_errors:
            print("Flow completed with errors:")
            for error in result.metadata.errors:
                print(f"  [{error['component']}] {error['message']}")

        return result

    except ComponentError as e:
        print(f"Component '{e.component}' failed: {e.message}")
        if e.original_error:
            print(f"  Caused by: {e.original_error}")
        raise

    except FlowTimeoutError as e:
        print(f"Flow timed out after {e.elapsed:.2f}s")
        print(f"  Step: {e.step}")
        raise

    except ConditionEvaluationError as e:
        print(f"Condition error: {e.message}")
        if e.condition:
            print(f"  Condition: {e.condition}")
        raise
```

### Error Recovery Pattern

```yaml
name: "Resilient Data Pipeline"

flow:
  settings:
    fail_fast: false  # Allow recovery

  steps:
    - component: primary_fetch
      description: "Try primary data source"
      on_error: skip  # If fails, try backup

    - component: backup_fetch
      description: "Fallback to backup source"
      condition: "context.data.primary_data is None"
      on_error: fail  # This must succeed

    - component: process_data
      on_error: continue  # Continue even if processing fails

    - component: error_reporter
      description: "Report any errors"
      condition: "len(context.metadata.errors) > 0"
```

---

## 4.2 Timeout Management

FlowEngine provides three timeout enforcement modes:

### Cooperative Mode (Default)

Components must call `check_deadline()` to respect timeouts:

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: cooperative  # Default
```

```python
class SlowComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        for item in large_dataset:
            self.check_deadline(context)  # Check periodically
            process_item(item)
        return context
```

**Advantages:**
- No overhead
- Clean shutdown
- Component controls granularity

**Disadvantages:**
- Requires component cooperation
- Non-cooperative components can overrun

### Strict Cooperative Enforcement

```yaml
flow:
  settings:
    timeout_mode: cooperative
    require_deadline_check: true  # Raise error if not checked
```

When a component takes >1 second without calling `check_deadline()`:
- Raises `DeadlineCheckError`
- Forces timeout compliance

### Hard Async Mode

Uses `asyncio.wait_for` for enforced cancellation:

```yaml
flow:
  settings:
    timeout_seconds: 10
    timeout_mode: hard_async
```

**Advantages:**
- Enforced timeout
- No component changes needed

**Disadvantages:**
- Asyncio overhead
- May not interrupt CPU-bound code

### Hard Process Mode

Runs each component in a separate process:

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: hard_process
```

**Advantages:**
- True hard timeout
- Survives infinite loops
- Process isolation

**Disadvantages:**
- Process creation overhead
- Context serialization required
- No shared state

### Choosing a Timeout Mode

```
┌─────────────────────────────────────────────────────────────────┐
│                    Choose Timeout Mode                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Components call check_deadline()?                               │
│    └── YES → Use cooperative (default, safest)                  │
│    └── NO  → Components do I/O operations?                      │
│                └── YES → Use hard_async                         │
│                └── NO  → Components are CPU-bound?              │
│                            └── YES → Use hard_process           │
│                            └── NO  → Use cooperative            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Timeout Guarantees

| Scenario | Cooperative | Hard Async | Hard Process |
|----------|-------------|------------|--------------|
| Between steps | Always | Always | Always |
| Component calls check_deadline() | Yes | Yes | Yes |
| Component blocks without checking | No | Yes | Yes |
| Teardown runs on timeout | Yes | Yes | Yes |

### Implementing Cooperative Timeout

```python
class BatchProcessorComponent(BaseComponent):
    """Component that processes items in batches with timeout awareness."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.batch_size = config.get("batch_size", 100)
        self.check_interval = config.get("check_interval", 10)

    def process(self, context: FlowContext) -> FlowContext:
        items = context.get("items", [])
        processed = []

        for i, item in enumerate(items):
            # Check deadline every N items
            if i % self.check_interval == 0:
                self.check_deadline(context)

            # Process item
            result = self._process_item(item)
            processed.append(result)

            # Also check before expensive operations
            if i % self.batch_size == 0:
                self.check_deadline(context)
                self._flush_batch(processed[-self.batch_size:])

        context.set("processed_items", processed)
        return context

    def _process_item(self, item):
        # Processing logic
        return {"id": item["id"], "processed": True}

    def _flush_batch(self, batch):
        # Batch save logic
        pass
```

---

## Exercise 4: Resilient File Processing

### Challenge

Build a file processing flow that:

1. **FileReaderComponent**: Read files from a directory
2. **ValidatorComponent**: Validate file format
3. **ProcessorComponent**: Process valid files
4. **ErrorReporterComponent**: Report any errors
5. Implement retry logic for failed files

### Requirements

- Use `fail_fast: false`
- Implement proper error handling
- Track and report errors

### Solution

<details>
<summary>Click to reveal solution</summary>

**Components (file_components.py):**

```python
from flowengine import BaseComponent, FlowContext
import time


class FileReaderComponent(BaseComponent):
    """Simulates reading files from a directory."""

    def process(self, context: FlowContext) -> FlowContext:
        # Simulated files (some will fail validation)
        files = [
            {"name": "report_2024.csv", "size": 1024, "type": "csv"},
            {"name": "data.json", "size": 512, "type": "json"},
            {"name": "notes.txt", "size": 256, "type": "txt"},
            {"name": "corrupted.csv", "size": 0, "type": "csv"},  # Will fail
            {"name": "large_file.csv", "size": 999999, "type": "csv"},  # Too large
        ]

        context.set("files", files)
        context.set("file_count", len(files))
        print(f"  [Reader] Found {len(files)} files")

        return context


class ValidatorComponent(BaseComponent):
    """Validates files and separates valid from invalid."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.allowed_types = config.get("allowed_types", ["csv", "json"])
        self.max_size = config.get("max_size", 10000)

    def process(self, context: FlowContext) -> FlowContext:
        files = context.get("files", [])
        valid_files = []
        invalid_files = []

        for file in files:
            errors = []

            if file["type"] not in self.allowed_types:
                errors.append(f"Invalid type: {file['type']}")

            if file["size"] == 0:
                errors.append("Empty file")

            if file["size"] > self.max_size:
                errors.append(f"File too large: {file['size']} bytes")

            if errors:
                invalid_files.append({"file": file, "errors": errors})
                print(f"  [Validator] Invalid: {file['name']} - {errors}")
            else:
                valid_files.append(file)
                print(f"  [Validator] Valid: {file['name']}")

        context.set("valid_files", valid_files)
        context.set("invalid_files", invalid_files)

        return context


class ProcessorComponent(BaseComponent):
    """Processes valid files with simulated work."""

    def process(self, context: FlowContext) -> FlowContext:
        valid_files = context.get("valid_files", [])
        processed = []
        failed = []

        for file in valid_files:
            # Check deadline for long operations
            self.check_deadline(context)

            try:
                # Simulate processing (might fail randomly)
                if "json" in file["name"]:
                    # Simulate a processing failure
                    raise RuntimeError("JSON parsing error")

                result = {
                    "name": file["name"],
                    "status": "processed",
                    "records": file["size"] // 10,
                }
                processed.append(result)
                print(f"  [Processor] Processed: {file['name']}")

            except Exception as e:
                failed.append({"file": file, "error": str(e)})
                print(f"  [Processor] Failed: {file['name']} - {e}")

        context.set("processed_files", processed)
        context.set("failed_files", failed)

        return context


class RetryComponent(BaseComponent):
    """Retries failed files with exponential backoff."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.max_retries = config.get("max_retries", 2)

    def process(self, context: FlowContext) -> FlowContext:
        failed_files = context.get("failed_files", [])

        if not failed_files:
            print("  [Retry] No files to retry")
            return context

        recovered = []
        permanently_failed = []

        for item in failed_files:
            file = item["file"]
            success = False

            for attempt in range(1, self.max_retries + 1):
                self.check_deadline(context)

                try:
                    # Simulate retry with decreasing failure rate
                    if attempt >= 2:  # Succeed on 2nd attempt
                        result = {
                            "name": file["name"],
                            "status": "recovered",
                            "attempt": attempt,
                        }
                        recovered.append(result)
                        print(f"  [Retry] Recovered: {file['name']} (attempt {attempt})")
                        success = True
                        break
                    else:
                        raise RuntimeError("Still failing")

                except Exception:
                    time.sleep(0.1 * attempt)  # Backoff

            if not success:
                permanently_failed.append(item)
                print(f"  [Retry] Permanently failed: {file['name']}")

        # Merge with already processed
        all_processed = context.get("processed_files", []) + recovered
        context.set("processed_files", all_processed)
        context.set("permanently_failed", permanently_failed)

        return context


class ErrorReporterComponent(BaseComponent):
    """Generates error report."""

    def process(self, context: FlowContext) -> FlowContext:
        invalid_files = context.get("invalid_files", [])
        permanently_failed = context.get("permanently_failed", [])
        processed_files = context.get("processed_files", [])

        report = {
            "summary": {
                "total_files": context.get("file_count", 0),
                "processed": len(processed_files),
                "invalid": len(invalid_files),
                "failed": len(permanently_failed),
            },
            "invalid_files": invalid_files,
            "failed_files": permanently_failed,
            "flow_errors": context.metadata.errors,
        }

        context.set("error_report", report)

        print(f"\n  [Reporter] === Error Report ===")
        print(f"  Total: {report['summary']['total_files']}")
        print(f"  Processed: {report['summary']['processed']}")
        print(f"  Invalid: {report['summary']['invalid']}")
        print(f"  Failed: {report['summary']['failed']}")

        return context
```

**YAML Configuration (file_flow.yaml):**

```yaml
name: "Resilient File Processing"
version: "1.0"
description: "Process files with error handling and retries"

components:
  - name: reader
    type: file_components.FileReaderComponent

  - name: validator
    type: file_components.ValidatorComponent
    config:
      allowed_types: ["csv", "json"]
      max_size: 10000

  - name: processor
    type: file_components.ProcessorComponent

  - name: retry
    type: file_components.RetryComponent
    config:
      max_retries: 3

  - name: reporter
    type: file_components.ErrorReporterComponent

flow:
  type: sequential
  settings:
    fail_fast: false  # Continue on errors
    timeout_seconds: 60
    timeout_mode: cooperative
  steps:
    - component: reader
      description: "Read files from directory"
      on_error: fail  # This must succeed

    - component: validator
      description: "Validate file formats"
      on_error: continue

    - component: processor
      description: "Process valid files"
      condition: "len(context.data.valid_files) > 0"
      on_error: continue  # Continue even if some fail

    - component: retry
      description: "Retry failed files"
      condition: "context.data.failed_files is not None and len(context.data.failed_files) > 0"
      on_error: continue

    - component: reporter
      description: "Generate error report"
      # Always runs to report status
```

**Execution:**

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine
from file_components import *


def main():
    config = ConfigLoader.load("file_flow.yaml")

    components = {
        "reader": FileReaderComponent("reader"),
        "validator": ValidatorComponent("validator"),
        "processor": ProcessorComponent("processor"),
        "retry": RetryComponent("retry"),
        "reporter": ErrorReporterComponent("reporter"),
    }

    engine = FlowEngine(config, components)
    result = engine.execute()

    # Access the error report
    report = result.data.error_report
    print(f"\n{'='*50}")
    print(f"Final Status: {report['summary']['processed']}/{report['summary']['total_files']} processed")

    # Check flow-level errors
    if result.metadata.has_errors:
        print("\nFlow-level errors:")
        for err in result.metadata.errors:
            print(f"  [{err['component']}] {err['message']}")


if __name__ == "__main__":
    main()
```

</details>

---

# Part 5: Advanced Patterns

## 5.1 Component Registry & Auto-Loading

### Using `FlowEngine.from_config()`

Instead of manually creating components, auto-load from YAML:

```python
from flowengine import ConfigLoader, FlowEngine

# Load config with type paths
config = ConfigLoader.load("flow.yaml")

# Auto-instantiate all components from their type paths
engine = FlowEngine.from_config(config)

# Execute
result = engine.execute()
```

**YAML with type paths:**

```yaml
components:
  - name: fetcher
    type: myapp.components.FetchComponent  # Full Python path
    config:
      url: "https://api.example.com"

  - name: processor
    type: myapp.components.ProcessComponent
    config:
      batch_size: 100
```

### Component Registry

Register components for reuse:

```python
from flowengine import ComponentRegistry, FlowEngine

# Create registry
registry = ComponentRegistry()

# Register component classes
registry.register_class("fetcher", FetchComponent)
registry.register_class("processor", ProcessComponent)

# Create instances
fetcher = registry.create("fetcher", "my_fetcher")

# Use with FlowEngine.from_config
engine = FlowEngine.from_config(config, registry=registry)

# Query registry
print(registry.list_registered())  # ["fetcher", "processor"]
cls = registry.get_class("fetcher")  # FetchComponent class
```

### Type Validation

Ensure components match their declared types:

```python
# Validate on engine creation (default)
engine = FlowEngine(config, components, validate_types=True)

# Manual validation
errors = engine.validate_component_types()
if errors:
    print(f"Type mismatches: {errors}")
```

---

## 5.2 Building Reusable Components

### Configuration-Driven Components

```python
class ConfigurableHTTPComponent(BaseComponent):
    """Flexible HTTP component with many configuration options."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.base_url = config.get("base_url", "")
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)
        self.headers = config.get("headers", {})
        self.method = config.get("method", "GET")

    def validate_config(self) -> list[str]:
        errors = []
        if not self.base_url:
            errors.append("base_url is required")
        if self.timeout <= 0:
            errors.append("timeout must be positive")
        if self.method not in ["GET", "POST", "PUT", "DELETE", "PATCH"]:
            errors.append(f"Invalid method: {self.method}")
        return errors

    def process(self, context: FlowContext) -> FlowContext:
        endpoint = context.get("endpoint", "/")
        url = f"{self.base_url}{endpoint}"

        # Implementation...
        return context
```

### Resource Management Pattern

```python
class PooledDatabaseComponent(BaseComponent):
    """Component with connection pooling."""

    _pool = None  # Class-level connection pool

    def init(self, config: dict) -> None:
        super().init(config)
        self.connection_string = config["connection_string"]
        self.pool_size = config.get("pool_size", 5)

        # Initialize pool once
        if PooledDatabaseComponent._pool is None:
            PooledDatabaseComponent._pool = create_pool(
                self.connection_string,
                size=self.pool_size
            )

    def setup(self, context: FlowContext) -> None:
        # Get connection from pool
        self._conn = self._pool.acquire()

    def process(self, context: FlowContext) -> FlowContext:
        result = self._conn.execute(context.get("query"))
        context.set("db_result", result)
        return context

    def teardown(self, context: FlowContext) -> None:
        # Return connection to pool
        if self._conn:
            self._pool.release(self._conn)
            self._conn = None

    def health_check(self) -> bool:
        return self._pool is not None and self._pool.is_healthy()
```

### Composable Components

```python
class TransformPipelineComponent(BaseComponent):
    """Component that chains multiple transformations."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.transforms = []

        # Build transformation pipeline from config
        for transform_config in config.get("transforms", []):
            transform_type = transform_config["type"]
            if transform_type == "normalize":
                self.transforms.append(self._normalize)
            elif transform_type == "filter":
                field = transform_config["field"]
                value = transform_config["value"]
                self.transforms.append(lambda x, f=field, v=value: self._filter(x, f, v))
            elif transform_type == "map":
                mapping = transform_config["mapping"]
                self.transforms.append(lambda x, m=mapping: self._map(x, m))

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("data", [])

        for transform in self.transforms:
            self.check_deadline(context)
            data = transform(data)

        context.set("transformed_data", data)
        return context

    def _normalize(self, data):
        # Normalize logic
        return data

    def _filter(self, data, field, value):
        return [item for item in data if item.get(field) == value]

    def _map(self, data, mapping):
        return [{mapping.get(k, k): v for k, v in item.items()} for item in data]
```

---

## 5.3 Real-World Patterns

### Pattern 1: ETL Pipeline

```yaml
name: "ETL Pipeline"
version: "1.0"

components:
  - name: extract_api
    type: myapp.extractors.APIExtractor
    config:
      base_url: "https://api.example.com"
      endpoint: "/data"

  - name: extract_db
    type: myapp.extractors.DatabaseExtractor
    config:
      connection_string: "${DB_CONNECTION}"
      query: "SELECT * FROM source_table"

  - name: transform
    type: myapp.transformers.DataTransformer
    config:
      operations:
        - type: normalize
        - type: deduplicate
          key: "id"
        - type: enrich
          lookup_table: "reference_data"

  - name: validate
    type: myapp.validators.SchemaValidator
    config:
      schema_path: "schemas/output_schema.json"

  - name: load
    type: myapp.loaders.DatabaseLoader
    config:
      connection_string: "${TARGET_DB}"
      table: "target_table"
      mode: "upsert"

  - name: notify
    type: myapp.notifiers.SlackNotifier
    config:
      webhook_url: "${SLACK_WEBHOOK}"

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 3600
    timeout_mode: hard_process
  steps:
    - component: extract_api
      description: "Extract from API"
      on_error: skip

    - component: extract_db
      description: "Extract from database"
      on_error: fail

    - component: transform
      description: "Transform data"
      condition: "context.data.raw_data is not None"

    - component: validate
      description: "Validate transformed data"
      on_error: continue

    - component: load
      description: "Load to target"
      condition: "context.data.validation.valid == True"
      on_error: fail

    - component: notify
      description: "Send completion notification"
```

### Pattern 2: Request Handler

```yaml
name: "API Request Handler"
version: "1.0"

components:
  - name: auth
    type: myapp.middleware.AuthMiddleware
    config:
      jwt_secret: "${JWT_SECRET}"

  - name: rate_limit
    type: myapp.middleware.RateLimiter
    config:
      requests_per_minute: 100

  - name: validate_request
    type: myapp.validators.RequestValidator
    config:
      schema: "request_schema.json"

  - name: handle_users
    type: myapp.handlers.UserHandler

  - name: handle_orders
    type: myapp.handlers.OrderHandler

  - name: handle_products
    type: myapp.handlers.ProductHandler

  - name: error_response
    type: myapp.handlers.ErrorResponseHandler

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 30
  steps:
    # Middleware chain (always runs)
    - component: auth
      on_error: fail

    - component: rate_limit
      on_error: fail

    - component: validate_request
      on_error: fail

    # Route to handler (conditional)
    - component: handle_users
      condition: "context.data.request.path.startswith('/users')"

    - component: handle_orders
      condition: "context.data.request.path.startswith('/orders')"

    - component: handle_products
      condition: "context.data.request.path.startswith('/products')"

    # Error handling
    - component: error_response
      condition: "context.data.response is None or context.metadata.has_errors"
```

### Pattern 3: Workflow with Approval

```yaml
name: "Document Approval Workflow"
version: "1.0"

flow:
  type: conditional  # Only one path executes

  steps:
    # Auto-approve small amounts
    - component: auto_approve
      condition: "context.data.amount < 1000"

    # Manager approval for medium amounts
    - component: manager_review
      condition: "context.data.amount >= 1000 and context.data.amount < 10000"

    # Director approval for large amounts
    - component: director_review
      condition: "context.data.amount >= 10000 and context.data.amount < 100000"

    # Executive approval for very large amounts
    - component: executive_review
      condition: "context.data.amount >= 100000"
```

---

## Exercise 5: Full ETL Pipeline

### Challenge

Build a complete ETL pipeline that:

1. **Extracts** data from multiple sources (CSV file, API simulation)
2. **Transforms** data (normalize, deduplicate, enrich)
3. **Validates** against a schema
4. **Loads** to a target (simulated database)
5. **Reports** on the operation

Include timeout protection and error handling.

### Solution

<details>
<summary>Click to reveal solution</summary>

**Components (etl_components.py):**

```python
from flowengine import BaseComponent, FlowContext
from datetime import datetime
import time


class CSVExtractorComponent(BaseComponent):
    """Extracts data from CSV source."""

    def process(self, context: FlowContext) -> FlowContext:
        # Simulated CSV data
        csv_data = [
            {"id": "1", "name": "Alice Smith", "email": "alice@example.com", "amount": "150.00"},
            {"id": "2", "name": "Bob Jones", "email": "bob@example.com", "amount": "250.50"},
            {"id": "3", "name": "Charlie Brown", "email": "charlie@example.com", "amount": "75.25"},
            {"id": "1", "name": "Alice Smith", "email": "alice@example.com", "amount": "150.00"},  # Duplicate
        ]

        context.set("csv_data", csv_data)
        print(f"  [CSVExtractor] Extracted {len(csv_data)} records from CSV")
        return context


class APIExtractorComponent(BaseComponent):
    """Extracts data from API source."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.endpoint = config.get("endpoint", "/users")

    def process(self, context: FlowContext) -> FlowContext:
        self.check_deadline(context)

        # Simulated API data
        api_data = [
            {"id": "4", "name": "Diana Prince", "email": "diana@example.com", "amount": "500.00"},
            {"id": "5", "name": "Eve Wilson", "email": "eve@example.com", "amount": "125.75"},
        ]

        context.set("api_data", api_data)
        print(f"  [APIExtractor] Fetched {len(api_data)} records from API")
        return context


class MergeComponent(BaseComponent):
    """Merges data from multiple sources."""

    def process(self, context: FlowContext) -> FlowContext:
        csv_data = context.get("csv_data", [])
        api_data = context.get("api_data", [])

        merged = csv_data + api_data
        context.set("merged_data", merged)
        context.set("source_counts", {
            "csv": len(csv_data),
            "api": len(api_data),
            "total": len(merged),
        })

        print(f"  [Merge] Combined {len(merged)} total records")
        return context


class NormalizeComponent(BaseComponent):
    """Normalizes data types and formats."""

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("merged_data", [])
        normalized = []

        for record in data:
            self.check_deadline(context)

            normalized_record = {
                "id": int(record["id"]),
                "name": record["name"].strip().title(),
                "email": record["email"].strip().lower(),
                "amount": float(record["amount"]),
                "processed_at": datetime.now().isoformat(),
            }
            normalized.append(normalized_record)

        context.set("normalized_data", normalized)
        print(f"  [Normalize] Normalized {len(normalized)} records")
        return context


class DeduplicateComponent(BaseComponent):
    """Removes duplicate records."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.key_field = config.get("key_field", "id")

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("normalized_data", [])
        seen = set()
        unique = []
        duplicates = 0

        for record in data:
            key = record[self.key_field]
            if key not in seen:
                seen.add(key)
                unique.append(record)
            else:
                duplicates += 1

        context.set("deduplicated_data", unique)
        context.set("duplicate_count", duplicates)

        print(f"  [Deduplicate] Removed {duplicates} duplicates, {len(unique)} unique records")
        return context


class EnrichComponent(BaseComponent):
    """Enriches data with additional information."""

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("deduplicated_data", [])

        # Simulated enrichment lookup
        tier_lookup = {
            "alice@example.com": "gold",
            "bob@example.com": "silver",
            "charlie@example.com": "bronze",
            "diana@example.com": "gold",
            "eve@example.com": "silver",
        }

        enriched = []
        for record in data:
            self.check_deadline(context)

            enriched_record = record.copy()
            enriched_record["tier"] = tier_lookup.get(record["email"], "standard")
            enriched_record["discount"] = {"gold": 0.2, "silver": 0.1, "bronze": 0.05}.get(
                enriched_record["tier"], 0
            )
            enriched.append(enriched_record)

        context.set("enriched_data", enriched)
        print(f"  [Enrich] Enriched {len(enriched)} records with tier info")
        return context


class ValidateComponent(BaseComponent):
    """Validates data against schema."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.required_fields = config.get("required_fields", ["id", "name", "email", "amount"])

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("enriched_data", [])
        valid_records = []
        invalid_records = []

        for record in data:
            errors = []

            for field in self.required_fields:
                if field not in record or record[field] is None:
                    errors.append(f"Missing required field: {field}")

            if record.get("amount", 0) < 0:
                errors.append("Amount cannot be negative")

            if errors:
                invalid_records.append({"record": record, "errors": errors})
            else:
                valid_records.append(record)

        context.set("valid_data", valid_records)
        context.set("invalid_data", invalid_records)
        context.set("validation_result", {
            "valid_count": len(valid_records),
            "invalid_count": len(invalid_records),
            "valid": len(invalid_records) == 0,
        })

        print(f"  [Validate] {len(valid_records)} valid, {len(invalid_records)} invalid")
        return context


class LoadComponent(BaseComponent):
    """Loads data to target destination."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.target = config.get("target", "database")
        self.mode = config.get("mode", "insert")

    def process(self, context: FlowContext) -> FlowContext:
        data = context.get("valid_data", [])

        # Simulate loading with progress
        loaded = 0
        for i, record in enumerate(data):
            self.check_deadline(context)
            # Simulate write
            time.sleep(0.01)
            loaded += 1

        context.set("load_result", {
            "target": self.target,
            "mode": self.mode,
            "records_loaded": loaded,
            "success": True,
        })

        print(f"  [Load] Loaded {loaded} records to {self.target}")
        return context


class ReportComponent(BaseComponent):
    """Generates ETL summary report."""

    def process(self, context: FlowContext) -> FlowContext:
        report = {
            "timestamp": datetime.now().isoformat(),
            "source_counts": context.get("source_counts", {}),
            "duplicate_count": context.get("duplicate_count", 0),
            "validation": context.get("validation_result", {}),
            "load_result": context.get("load_result", {}),
            "execution": {
                "flow_id": context.metadata.flow_id,
                "duration": context.metadata.total_duration,
                "steps": len(context.metadata.step_timings),
            },
        }

        context.set("etl_report", report)

        print("\n  [Report] === ETL Summary ===")
        print(f"  Sources: {report['source_counts']}")
        print(f"  Duplicates removed: {report['duplicate_count']}")
        print(f"  Validation: {report['validation']}")
        print(f"  Loaded: {report['load_result'].get('records_loaded', 0)} records")
        print(f"  Duration: {report['execution']['duration']:.3f}s")

        return context
```

**YAML Configuration (etl_flow.yaml):**

```yaml
name: "Complete ETL Pipeline"
version: "1.0"
description: "Extract, Transform, Load with validation and reporting"

components:
  - name: extract_csv
    type: etl_components.CSVExtractorComponent

  - name: extract_api
    type: etl_components.APIExtractorComponent
    config:
      endpoint: "/users"

  - name: merge
    type: etl_components.MergeComponent

  - name: normalize
    type: etl_components.NormalizeComponent

  - name: deduplicate
    type: etl_components.DeduplicateComponent
    config:
      key_field: "id"

  - name: enrich
    type: etl_components.EnrichComponent

  - name: validate
    type: etl_components.ValidateComponent
    config:
      required_fields: ["id", "name", "email", "amount"]

  - name: load
    type: etl_components.LoadComponent
    config:
      target: "warehouse"
      mode: "upsert"

  - name: report
    type: etl_components.ReportComponent

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 300
    timeout_mode: cooperative
    require_deadline_check: true
  steps:
    # Extract phase
    - component: extract_csv
      description: "Extract from CSV file"
      on_error: skip

    - component: extract_api
      description: "Extract from API"
      on_error: skip

    - component: merge
      description: "Merge data sources"
      condition: "context.data.csv_data is not None or context.data.api_data is not None"

    # Transform phase
    - component: normalize
      description: "Normalize data types"
      condition: "context.data.merged_data is not None"

    - component: deduplicate
      description: "Remove duplicates"
      condition: "context.data.normalized_data is not None"

    - component: enrich
      description: "Enrich with additional data"
      condition: "context.data.deduplicated_data is not None"

    # Validate phase
    - component: validate
      description: "Validate against schema"
      condition: "context.data.enriched_data is not None"

    # Load phase
    - component: load
      description: "Load to warehouse"
      condition: "context.data.validation_result.valid == True"
      on_error: fail

    # Report phase
    - component: report
      description: "Generate summary report"
```

**Execution:**

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine
from etl_components import *


def main():
    config = ConfigLoader.load("etl_flow.yaml")

    components = {
        "extract_csv": CSVExtractorComponent("extract_csv"),
        "extract_api": APIExtractorComponent("extract_api"),
        "merge": MergeComponent("merge"),
        "normalize": NormalizeComponent("normalize"),
        "deduplicate": DeduplicateComponent("deduplicate"),
        "enrich": EnrichComponent("enrich"),
        "validate": ValidateComponent("validate"),
        "load": LoadComponent("load"),
        "report": ReportComponent("report"),
    }

    engine = FlowEngine(config, components)

    print("Starting ETL Pipeline...")
    print("=" * 50)

    result = engine.execute()

    print("\n" + "=" * 50)
    print("ETL Pipeline Complete")

    # Show detailed timing
    print("\n--- Step Timing ---")
    for step in result.metadata.step_timings:
        print(f"  {step.component}: {step.duration:.4f}s")

    if result.metadata.skipped_components:
        print(f"\nSkipped: {result.metadata.skipped_components}")


if __name__ == "__main__":
    main()
```

</details>

---

# Part 6: Built-in Components

## 6.1 LoggingComponent

Debug flows by logging context state at specific points.

### Configuration

```yaml
- name: debug_log
  type: flowengine.contrib.logging.LoggingComponent
  config:
    level: debug      # debug, info, warning, error
    message: "After processing"  # Custom message
    log_data: true    # Log context.data
    log_metadata: false  # Log execution metadata
    keys:             # Specific keys to log (optional)
      - user
      - result
```

### Usage Example

```yaml
name: "Pipeline with Debug Logging"

components:
  - name: processor
    type: myapp.ProcessorComponent

  - name: debug_after_process
    type: flowengine.contrib.logging.LoggingComponent
    config:
      level: debug
      message: "After processing step"
      log_data: true
      keys:
        - processed_data
        - stats

flow:
  steps:
    - component: processor
    - component: debug_after_process
      condition: "context.data.debug_mode == True"
```

### Programmatic Usage

```python
from flowengine.contrib.logging import LoggingComponent

logger = LoggingComponent("debug")
logger.init({
    "level": "info",
    "message": "Current state",
    "log_data": True,
    "log_metadata": True,
})

result = logger.process(context)
# Logs context data and metadata at INFO level
```

---

## 6.2 HTTPComponent

Make HTTP requests and store responses in context.

### Installation

```bash
pip install flowengine[http]  # Requires httpx
```

### Configuration

```yaml
- name: api_client
  type: flowengine.contrib.http.HTTPComponent
  config:
    base_url: "https://api.example.com"  # Required
    timeout: 30                           # Request timeout (seconds)
    method: GET                           # GET, POST, PUT, PATCH, DELETE
    headers:                              # Optional headers
      Authorization: "Bearer ${API_TOKEN}"
      Content-Type: "application/json"
    endpoint_key: "endpoint"              # Context key for path
    result_key: "api_result"              # Key to store response
```

### Usage Example

```yaml
name: "API Integration Flow"

components:
  - name: fetch_users
    type: flowengine.contrib.http.HTTPComponent
    config:
      base_url: "https://api.example.com"
      timeout: 30
      method: GET
      headers:
        Authorization: "Bearer ${API_TOKEN}"
      result_key: "users_response"

  - name: create_user
    type: flowengine.contrib.http.HTTPComponent
    config:
      base_url: "https://api.example.com"
      timeout: 30
      method: POST
      headers:
        Content-Type: "application/json"
      result_key: "create_response"

flow:
  steps:
    - component: fetch_users
      # Set endpoint in context before calling

    - component: create_user
      condition: "context.data.users_response.status_code == 200"
```

### Programmatic Usage

```python
from flowengine.contrib.http import HTTPComponent

http = HTTPComponent("api")
http.init({
    "base_url": "https://api.example.com",
    "timeout": 30,
    "method": "GET",
    "headers": {"Authorization": "Bearer token"},
})

context = FlowContext()
context.set("endpoint", "/users/123")

http.setup(context)  # Creates HTTP client
result = http.process(context)
http.teardown(context)  # Closes client

# Access response
print(result.data.api.status_code)  # 200
print(result.data.api.data)         # Response JSON
print(result.data.api.headers)      # Response headers
```

---

# Part 7: Testing & Debugging

## 7.1 Unit Testing Components

Test components in isolation:

```python
import pytest
from flowengine import FlowContext
from my_components import CalculatorComponent


class TestCalculatorComponent:
    """Unit tests for CalculatorComponent."""

    @pytest.fixture
    def component(self):
        """Create component instance."""
        comp = CalculatorComponent("calc")
        comp.init({"precision": 2})
        return comp

    @pytest.fixture
    def context(self):
        """Create fresh context."""
        return FlowContext()

    def test_process_adds_correctly(self, component, context):
        """Test addition operation."""
        context.set("a", 10)
        context.set("b", 5)
        context.set("operation", "add")

        result = component.process(context)

        assert result.get("result") == 15

    def test_process_with_invalid_operation(self, component, context):
        """Test handling of invalid operation."""
        context.set("a", 10)
        context.set("b", 5)
        context.set("operation", "invalid")

        with pytest.raises(ValueError, match="Unknown operation"):
            component.process(context)

    def test_validate_config_missing_required(self):
        """Test configuration validation."""
        comp = CalculatorComponent("calc")
        comp.init({})  # Missing precision

        errors = comp.validate_config()

        assert "precision is required" in errors

    def test_lifecycle_methods_called(self, component, context):
        """Test setup and teardown are called."""
        component.setup(context)
        assert context.get("calc_setup") is True

        component.teardown(context)
        assert context.get("calc_teardown") is True
```

---

## 7.2 Integration Testing Flows

Test complete flow execution:

```python
import pytest
from flowengine import ConfigLoader, FlowContext, FlowEngine
from my_components import *


class TestOrderProcessingFlow:
    """Integration tests for order processing flow."""

    @pytest.fixture
    def engine(self):
        """Create flow engine."""
        config = ConfigLoader.load("order_flow.yaml")
        components = {
            "validator": ValidatorComponent("validator"),
            "calculator": CalculatorComponent("calculator"),
            "discounter": DiscountComponent("discounter"),
        }
        return FlowEngine(config, components)

    def test_valid_order_processed(self, engine):
        """Test valid order is fully processed."""
        context = FlowContext()
        context.set("order", {
            "customer_id": "CUST-001",
            "items": [
                {"name": "Widget", "price": 50.00, "quantity": 3},
            ],
        })

        result = engine.execute(context)

        assert result.get("validation")["valid"] is True
        assert result.get("subtotal") == 150.00
        assert result.get("final_total") is not None

    def test_invalid_order_stops_processing(self, engine):
        """Test invalid order doesn't reach calculator."""
        context = FlowContext()
        context.set("order", {"items": []})  # Missing customer_id

        result = engine.execute(context)

        assert result.get("validation")["valid"] is False
        assert result.get("subtotal") is None  # Calculator didn't run
        assert "calculator" in result.metadata.skipped_components

    def test_flow_tracks_metadata(self, engine):
        """Test execution metadata is tracked."""
        context = FlowContext()
        context.set("order", {
            "customer_id": "CUST-001",
            "items": [{"name": "Widget", "price": 100.00, "quantity": 1}],
        })

        result = engine.execute(context)

        assert result.metadata.flow_id is not None
        assert result.metadata.total_duration > 0
        assert len(result.metadata.step_timings) == 3
        assert "validator" in result.metadata.component_timings

    def test_timeout_is_enforced(self, engine):
        """Test flow timeout is enforced."""
        # Modify engine timeout for test
        engine.timeout = 0.001  # Very short

        context = FlowContext()
        context.set("order", {...})

        with pytest.raises(FlowTimeoutError):
            engine.execute(context)
```

---

## 7.3 Debugging with Dry-Run and Metadata

### Dry-Run Execution

Preview which steps would execute without running them:

```python
from flowengine import ConfigLoader, FlowContext, FlowEngine

config = ConfigLoader.load("flow.yaml")
engine = FlowEngine(config, components)

# Prepare context with test data
context = FlowContext()
context.set("status", "active")
context.set("amount", 150)

# See which steps would execute
steps = engine.dry_run(context)
print(f"Would execute: {steps}")
# Output: ["validator", "processor", "notifier"]

# Compare with actual execution
result = engine.execute(context)
executed = list(result.metadata.component_timings.keys())
assert steps == executed  # Should match
```

### Metadata Inspection

```python
def debug_execution(result):
    """Debug helper to inspect execution details."""
    m = result.metadata

    print("\n=== Execution Debug ===")
    print(f"Flow ID: {m.flow_id}")
    print(f"Duration: {m.total_duration:.3f}s")

    print("\n--- Steps ---")
    for step in m.step_timings:
        print(f"  [{step.step_index}] {step.component}: {step.duration:.4f}s")

    print("\n--- Skipped ---")
    for comp in m.skipped_components:
        print(f"  - {comp}")

    print("\n--- Errors ---")
    for error in m.errors:
        print(f"  [{error['component']}] {error['message']}")

    print("\n--- Context Data ---")
    for key, value in result.data.to_dict().items():
        value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
        print(f"  {key}: {value_str}")


# Usage
result = engine.execute(context)
debug_execution(result)
```

### Adding Debug Logging

```yaml
# Add debug steps to your flow
steps:
  - component: processor

  - component: debug_checkpoint_1
    type: flowengine.contrib.logging.LoggingComponent
    config:
      level: debug
      message: "After processor"
      log_data: true

  - component: transformer
    condition: "context.data.process_result is not None"

  - component: debug_checkpoint_2
    type: flowengine.contrib.logging.LoggingComponent
    config:
      level: debug
      message: "After transformer"
      log_data: true
      keys: ["transformed_data"]
```

---

# Appendix A: Complete YAML Examples

## A.1 Simple Sequential Pipeline

```yaml
# simple_pipeline.yaml
name: "Simple Data Pipeline"
version: "1.0"
description: "Basic sequential data processing flow"

components:
  - name: reader
    type: myapp.components.DataReaderComponent
    config:
      source: "input.csv"

  - name: transformer
    type: myapp.components.TransformComponent
    config:
      operations: ["normalize", "clean"]

  - name: writer
    type: myapp.components.DataWriterComponent
    config:
      destination: "output.csv"

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 300
  steps:
    - component: reader
      description: "Read input data"

    - component: transformer
      description: "Transform data"

    - component: writer
      description: "Write output data"
```

## A.2 Conditional Branching

```yaml
# conditional_branching.yaml
name: "Payment Processor"
version: "1.0"
description: "Routes payments based on amount and type"

components:
  - name: validate_payment
    type: payments.ValidatorComponent

  - name: process_credit
    type: payments.CreditCardProcessor

  - name: process_debit
    type: payments.DebitCardProcessor

  - name: process_bank
    type: payments.BankTransferProcessor

  - name: process_large
    type: payments.LargePaymentProcessor

  - name: notify_success
    type: payments.SuccessNotifier

  - name: notify_failure
    type: payments.FailureNotifier

flow:
  type: sequential
  settings:
    fail_fast: false
  steps:
    # Validation always runs first
    - component: validate_payment
      on_error: fail

    # Route based on payment type
    - component: process_large
      condition: "context.data.payment.amount >= 10000"

    - component: process_credit
      condition: "context.data.payment.type == 'credit' and context.data.payment.amount < 10000"

    - component: process_debit
      condition: "context.data.payment.type == 'debit' and context.data.payment.amount < 10000"

    - component: process_bank
      condition: "context.data.payment.type == 'bank' and context.data.payment.amount < 10000"

    # Notification based on result
    - component: notify_success
      condition: "context.data.payment_result.status == 'success'"

    - component: notify_failure
      condition: "context.data.payment_result.status != 'success'"
```

## A.3 ETL Pipeline with Error Recovery

```yaml
# data_etl.yaml
name: "Data ETL Pipeline"
version: "2.0"
description: "Robust ETL with error recovery and retries"

components:
  - name: extract_primary
    type: etl.PrimaryExtractor
    config:
      source: "https://primary-api.example.com"
      timeout: 30

  - name: extract_backup
    type: etl.BackupExtractor
    config:
      source: "https://backup-api.example.com"
      timeout: 60

  - name: transform
    type: etl.DataTransformer
    config:
      schema: "schemas/v2.json"
      operations:
        - type: normalize
        - type: deduplicate
          key: id
        - type: validate

  - name: load_warehouse
    type: etl.WarehouseLoader
    config:
      connection: "${WAREHOUSE_CONNECTION}"
      table: "fact_data"
      mode: upsert

  - name: load_cache
    type: etl.CacheLoader
    config:
      redis_url: "${REDIS_URL}"
      ttl: 3600

  - name: error_handler
    type: etl.ErrorHandler
    config:
      slack_webhook: "${SLACK_WEBHOOK}"

  - name: metrics
    type: etl.MetricsReporter
    config:
      endpoint: "${METRICS_ENDPOINT}"

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 3600
    timeout_mode: hard_process
  steps:
    # Extraction with fallback
    - component: extract_primary
      description: "Extract from primary source"
      on_error: skip

    - component: extract_backup
      description: "Fallback to backup source"
      condition: "context.data.extracted_data is None"
      on_error: fail

    # Transformation
    - component: transform
      description: "Transform and validate data"
      condition: "context.data.extracted_data is not None"
      on_error: continue

    # Loading (parallel targets)
    - component: load_warehouse
      description: "Load to data warehouse"
      condition: "context.data.transformed_data is not None"
      on_error: continue

    - component: load_cache
      description: "Update cache"
      condition: "context.data.transformed_data is not None"
      on_error: continue

    # Error handling and metrics (always run)
    - component: error_handler
      description: "Handle and report errors"
      condition: "context.metadata.has_errors"

    - component: metrics
      description: "Report execution metrics"
```

## A.4 Request Router

```yaml
# request_router.yaml
name: "API Request Router"
version: "1.0"
description: "Routes API requests to appropriate handlers"

components:
  - name: auth
    type: middleware.AuthMiddleware
    config:
      jwt_secret: "${JWT_SECRET}"
      exempt_paths: ["/health", "/login"]

  - name: rate_limiter
    type: middleware.RateLimiter
    config:
      requests_per_minute: 100
      burst_size: 20

  - name: handle_health
    type: handlers.HealthHandler

  - name: handle_users
    type: handlers.UserHandler

  - name: handle_orders
    type: handlers.OrderHandler

  - name: handle_products
    type: handlers.ProductHandler

  - name: handle_not_found
    type: handlers.NotFoundHandler

  - name: response_formatter
    type: middleware.ResponseFormatter
    config:
      format: json

flow:
  type: sequential
  settings:
    fail_fast: false
    timeout_seconds: 30
  steps:
    # Middleware (always run)
    - component: auth
      on_error: fail

    - component: rate_limiter
      on_error: fail

    # Routing (only one matches)
    - component: handle_health
      condition: "context.data.request.path == '/health'"

    - component: handle_users
      condition: "context.data.request.path.startswith('/users')"

    - component: handle_orders
      condition: "context.data.request.path.startswith('/orders')"

    - component: handle_products
      condition: "context.data.request.path.startswith('/products')"

    - component: handle_not_found
      condition: "context.data.response is None"

    # Response formatting (always run)
    - component: response_formatter
```

## A.5 Workflow with Timeout Modes

```yaml
# timeout_demo.yaml
name: "Timeout Modes Demo"
version: "1.0"
description: "Demonstrates different timeout enforcement modes"

components:
  - name: fast_component
    type: demo.FastComponent
    config:
      duration: 0.1

  - name: slow_component
    type: demo.SlowComponent
    config:
      duration: 5.0

  - name: cooperative_component
    type: demo.CooperativeComponent
    config:
      iterations: 100
      check_interval: 10

flow:
  type: sequential
  settings:
    timeout_seconds: 2
    timeout_mode: cooperative        # Try: cooperative, hard_async, hard_process
    require_deadline_check: true     # Enforce deadline checks
  steps:
    - component: fast_component
      description: "Quick operation"

    - component: cooperative_component
      description: "Long operation with deadline checks"

    - component: slow_component
      description: "Potentially slow operation"
```

## A.6 Multi-Stage Approval Workflow

```yaml
# approval_workflow.yaml
name: "Document Approval Workflow"
version: "1.0"
description: "Multi-level document approval based on amount"

components:
  - name: validate_document
    type: workflow.DocumentValidator

  - name: auto_approve
    type: workflow.AutoApprover
    config:
      max_amount: 1000

  - name: manager_approval
    type: workflow.ManagerApproval
    config:
      timeout_days: 2

  - name: director_approval
    type: workflow.DirectorApproval
    config:
      timeout_days: 5

  - name: executive_approval
    type: workflow.ExecutiveApproval
    config:
      timeout_days: 7

  - name: notify_requester
    type: workflow.RequesterNotifier

  - name: archive_document
    type: workflow.DocumentArchiver

flow:
  type: sequential
  settings:
    fail_fast: true
    timeout_seconds: 86400  # 24 hours
  steps:
    # Validation
    - component: validate_document
      description: "Validate document format and required fields"

    # Approval routing (amount-based)
    - component: auto_approve
      description: "Auto-approve small amounts"
      condition: "context.data.document.amount < 1000"

    - component: manager_approval
      description: "Manager approval for medium amounts"
      condition: |
        context.data.document.amount >= 1000 and
        context.data.document.amount < 10000

    - component: director_approval
      description: "Director approval for large amounts"
      condition: |
        context.data.document.amount >= 10000 and
        context.data.document.amount < 100000

    - component: executive_approval
      description: "Executive approval for very large amounts"
      condition: "context.data.document.amount >= 100000"

    # Post-approval
    - component: notify_requester
      description: "Notify requester of decision"
      condition: "context.data.approval_result is not None"

    - component: archive_document
      description: "Archive approved document"
      condition: "context.data.approval_result.approved == True"
```

---

# Appendix B: Common Patterns Cheat Sheet

## Component Lifecycle

```python
class MyComponent(BaseComponent):
    def __init__(self, name): super().__init__(name)  # Required
    def init(self, config): ...           # One-time setup
    def setup(self, context): ...         # Per-execution setup
    def process(self, context): ...       # Main logic (REQUIRED)
    def teardown(self, context): ...      # Per-execution cleanup
    def validate_config(self): ...        # Config validation
    def health_check(self): ...           # Health check
    def check_deadline(self, context): ...  # Timeout check
```

## Context Operations

```python
# Set/Get
context.set("key", value)
value = context.get("key", default)

# Dot notation
context.data.user.name
context.data.items[0]

# Check existence
if context.has("key"): ...

# Serialization
json_str = context.to_json()
context = FlowContext.from_json(json_str)
```

## Flow Types

```yaml
# Sequential: All matching steps run
flow:
  type: sequential
  steps:
    - component: a
    - component: b  # Also runs if condition True
      condition: "..."

# Conditional: First match wins
flow:
  type: conditional
  steps:
    - component: a
      condition: "..."
    - component: b  # Only runs if a's condition was False
      condition: "..."
```

## Error Handling

```yaml
# Global
settings:
  fail_fast: true          # Stop on first error
  on_condition_error: skip # fail/skip/warn

# Per-step
steps:
  - component: x
    on_error: continue     # fail/skip/continue
```

## Timeout Modes

```yaml
settings:
  timeout_seconds: 60
  timeout_mode: cooperative    # Default
  # timeout_mode: hard_async   # Asyncio enforcement
  # timeout_mode: hard_process # Process isolation
  require_deadline_check: true # Enforce check_deadline()
```

## Conditions

```python
# Valid conditions
"context.data.x == 'value'"
"context.data.count > 0"
"context.data.items is not None"
"context.data.status in ['a', 'b']"
"context.data.a and context.data.b"
```

---

# Appendix C: Troubleshooting Guide

## Common Errors

### ConfigurationError: Component not found

**Symptom:** `FlowExecutionError: Component not found: my_component`

**Cause:** Component name in steps doesn't match components dict

**Solution:**
```python
# Check component names match
components = {
    "my_component": MyComponent("my_component"),  # Must match YAML
}
```

### ConditionEvaluationError

**Symptom:** `ConditionEvaluationError: Unsafe expression`

**Cause:** Using function calls in conditions

**Solution:**
```yaml
# Wrong
condition: "len(context.data.items) > 0"

# Right
condition: "context.data.items is not None"
```

### FlowTimeoutError

**Symptom:** `FlowTimeoutError: Deadline exceeded`

**Solution:**
```python
# In long-running components:
def process(self, context):
    for item in items:
        self.check_deadline(context)  # Add this
        process_item(item)
```

### DeadlineCheckError

**Symptom:** `DeadlineCheckError: Component never called check_deadline()`

**Cause:** `require_deadline_check: true` but component doesn't check

**Solution:**
```python
def process(self, context):
    self.check_deadline(context)  # Add deadline checks
    # ... processing
```

### Missing Context Data

**Symptom:** `None` returned from `context.get()`

**Cause:** Previous step didn't set the expected key

**Solution:**
```python
# Check if data exists in condition
condition: "context.data.result is not None"

# Or use default in code
value = context.get("result", default_value)
```

## Debugging Tips

1. **Add logging steps:** Use `LoggingComponent` between steps
2. **Use dry-run:** Preview execution path with `engine.dry_run()`
3. **Check metadata:** Inspect `result.metadata.skipped_components`
4. **Validate first:** Call `engine.validate()` before execute
5. **Lower timeouts:** Use short timeouts during development

## Performance Tips

1. **Use cooperative timeout:** Lower overhead than hard modes
2. **Check deadline strategically:** Not every iteration, but periodically
3. **Minimize context data:** Only store what you need
4. **Use fail_fast:** Stop early on errors
5. **Profile with metadata:** Use `step_timings` to find bottlenecks

---

## Summary

This tutorial covered:

1. **Getting Started:** Components, flows, lifecycle
2. **Configuration:** YAML structure, flow types, conditions
3. **Data Flow:** Context, DotDict, metadata
4. **Error Handling:** Strategies, timeout modes
5. **Advanced Patterns:** Registry, reusable components, real-world examples
6. **Built-in Components:** LoggingComponent, HTTPComponent
7. **Testing:** Unit tests, integration tests, debugging

FlowEngine enables you to build maintainable, observable, and resilient data pipelines with a declarative YAML-driven approach. Start simple, add complexity as needed, and leverage the rich metadata to understand your flow's behavior.

**Happy flowing!**
