# Condition Expressions

Conditions control when steps execute. FlowEngine uses safe Python expressions that are validated against an AST allowlist to prevent code injection.

---

## Basic Syntax

Conditions are Python expressions that evaluate to `True` or `False`:

```yaml
steps:
  - component: process_order
    condition: "context.data.order_status == 'pending'"
```

The expression has access to the `context` object, allowing you to check runtime state.

---

## Accessing Context Data

### Direct Access

```yaml
condition: "context.data.user_id == 123"
condition: "context.data.is_active == True"
condition: "context.data.items is not None"
```

### Nested Access (Dot Notation)

```yaml
condition: "context.data.user.profile.verified == True"
condition: "context.data.order.items[0].quantity > 0"
```

### Checking Existence

```yaml
condition: "context.data.optional_field is not None"
condition: "context.data.results is None"
```

---

## Allowed Operators

### Comparison Operators

| Operator | Example |
|----------|---------|
| `==` | `context.data.status == 'active'` |
| `!=` | `context.data.status != 'deleted'` |
| `<` | `context.data.count < 100` |
| `<=` | `context.data.count <= 100` |
| `>` | `context.data.count > 0` |
| `>=` | `context.data.count >= 10` |

### Logical Operators

| Operator | Example |
|----------|---------|
| `and` | `context.data.a == 1 and context.data.b == 2` |
| `or` | `context.data.status == 'a' or context.data.status == 'b'` |
| `not` | `not context.data.is_disabled` |

### Identity Operators

| Operator | Example |
|----------|---------|
| `is` | `context.data.value is None` |
| `is not` | `context.data.value is not None` |

### Membership Operators

| Operator | Example |
|----------|---------|
| `in` | `context.data.status in ['active', 'pending']` |
| `not in` | `context.data.role not in ['guest', 'banned']` |

---

## Allowed Values

### Constants

```yaml
condition: "context.data.active == True"
condition: "context.data.deleted == False"
condition: "context.data.value is None"
```

### Numbers

```yaml
condition: "context.data.count > 100"
condition: "context.data.price <= 99.99"
condition: "context.data.quantity == 0"
```

### Strings

```yaml
condition: "context.data.status == 'active'"
condition: "context.data.type == \"order\""
```

### Lists

```yaml
condition: "context.data.role in ['admin', 'moderator']"
condition: "context.data.tags == ['urgent', 'important']"
```

---

## Complex Conditions

### Multiple Conditions

```yaml
condition: "context.data.user.active == True and context.data.user.verified == True"
```

### Grouped Conditions

```yaml
condition: "(context.data.role == 'admin' or context.data.role == 'superuser') and context.data.enabled == True"
```

### Nested Access with Checks

```yaml
condition: "context.data.order is not None and context.data.order.total > 0"
```

---

## Disallowed Expressions

For security, the following are **not allowed**:

### Function Calls

```yaml
# ❌ NOT ALLOWED
condition: "len(context.data.items) > 0"
condition: "str(context.data.count)"
condition: "context.data.name.lower() == 'admin'"
```

**Workaround**: Use direct comparisons or set flags in components.

### Imports

```yaml
# ❌ NOT ALLOWED
condition: "import os; os.system('rm -rf /')"
```

### Assignments

```yaml
# ❌ NOT ALLOWED
condition: "context.data.hacked = True"
```

### Lambda Expressions

```yaml
# ❌ NOT ALLOWED
condition: "(lambda: True)()"
```

### Comprehensions

```yaml
# ❌ NOT ALLOWED
condition: "[x for x in context.data.items if x > 0]"
```

---

## Condition Error Handling

Configure how the engine handles invalid conditions:

```yaml
flow:
  settings:
    on_condition_error: fail  # fail, skip, or warn
```

| Mode | Behavior |
|------|----------|
| `fail` | Raise `ConditionEvaluationError` (default) |
| `skip` | Skip the step, log error |
| `warn` | Skip the step, log warning |

### Programmatic Handling

```python
from flowengine import ConditionEvaluationError

try:
    result = engine.execute()
except ConditionEvaluationError as e:
    print(f"Invalid condition: {e.condition}")
    print(f"Error: {e.message}")
```

---

## Validating Conditions

Check conditions before execution:

```python
from flowengine import ConditionEvaluator

evaluator = ConditionEvaluator()

# Check if safe
if evaluator.is_safe("context.data.status == 'active'"):
    print("Condition is safe")

# Get validation errors
errors = evaluator.validate("len(context.data.items) > 0")
if errors:
    print("Validation errors:", errors)
# Output: ["Function calls are not allowed"]
```

---

## Practical Examples

### Status-Based Routing

```yaml
steps:
  - component: handle_new
    condition: "context.data.order.status == 'new'"

  - component: handle_processing
    condition: "context.data.order.status == 'processing'"

  - component: handle_complete
    condition: "context.data.order.status == 'complete'"

  - component: handle_cancelled
    condition: "context.data.order.status == 'cancelled'"
```

### Role-Based Access

```yaml
steps:
  - component: admin_panel
    condition: "context.data.user.role in ['admin', 'superuser']"

  - component: moderator_panel
    condition: "context.data.user.role == 'moderator'"

  - component: user_dashboard
    condition: "context.data.user.role == 'user'"
```

### Threshold Checks

```yaml
steps:
  - component: send_alert
    condition: "context.data.error_count >= 10"

  - component: scale_up
    condition: "context.data.cpu_usage > 80 and context.data.auto_scale == True"
```

### Success/Failure Branching

```yaml
steps:
  - component: fetch_data
    on_error: continue

  - component: process_data
    condition: "context.data.fetch_status == 'success'"

  - component: use_cache
    condition: "context.data.fetch_status != 'success'"
```

### Metadata-Based Conditions

```yaml
steps:
  - component: error_handler
    condition: "context.metadata.has_errors == True"

  - component: success_handler
    condition: "context.metadata.has_errors == False"
```

---

## Best Practices

1. **Keep conditions simple**: Complex logic belongs in components
2. **Use status flags**: Set explicit flags rather than complex expressions
3. **Avoid deep nesting**: `context.data.a.b.c.d.e` is hard to maintain
4. **Check for None**: Guard against missing data with `is not None`
5. **Use constants**: Prefer `== 'active'` over magic strings scattered throughout
6. **Test conditions**: Use `dry_run()` to verify condition logic

---

## Next Steps

- [Timeout Modes](timeout-modes.md) - Protect long-running flows
- [Error Handling](error-handling.md) - Handle condition errors
- [API Reference](../api/eval.md) - ConditionEvaluator API
