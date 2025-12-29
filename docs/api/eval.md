# Evaluation Module

Safe expression evaluation for conditions.

---

## ConditionEvaluator

Safely evaluates condition expressions against flow context.

::: flowengine.eval.evaluator.ConditionEvaluator
    options:
      show_source: false
      members:
        - __init__
        - evaluate
        - is_safe
        - validate

---

## SafeASTValidator

Validates Python AST for safe expressions only.

::: flowengine.eval.safe_ast.SafeASTValidator
    options:
      show_source: false
      members:
        - __init__
        - validate
        - get_errors

---

## Allowed Expression Constructs

### Comparison Operators

| Operator | Example |
|----------|---------|
| `==` | `context.data.status == 'active'` |
| `!=` | `context.data.status != 'deleted'` |
| `<` | `context.data.count < 100` |
| `<=` | `context.data.count <= 100` |
| `>` | `context.data.count > 0` |
| `>=` | `context.data.count >= 10` |

### Boolean Operators

| Operator | Example |
|----------|---------|
| `and` | `a == 1 and b == 2` |
| `or` | `status == 'a' or status == 'b'` |
| `not` | `not is_disabled` |

### Identity and Membership

| Operator | Example |
|----------|---------|
| `is` | `value is None` |
| `is not` | `value is not None` |
| `in` | `status in ['active', 'pending']` |
| `not in` | `role not in ['guest']` |

### Attribute and Subscript Access

```python
context.data.user.name          # Attribute access
context.data.items[0]           # Index access
context.data["key"]             # Key access
```

### Literals

```python
True, False, None               # Boolean and None
42, 3.14, -1                    # Numbers
"string", 'string'              # Strings
[1, 2, 3]                       # Lists
("a", "b")                      # Tuples
{"key": "value"}                # Dicts
```

---

## Disallowed Constructs

These are blocked for security:

| Construct | Example | Reason |
|-----------|---------|--------|
| Function calls | `len(x)` | Code execution |
| Imports | `import os` | Module access |
| Assignments | `x = 1` | State mutation |
| Lambda | `lambda: x` | Code execution |
| Comprehensions | `[x for x in y]` | Complex logic |

---

## Usage Examples

### Basic Evaluation

```python
from flowengine import ConditionEvaluator, FlowContext

evaluator = ConditionEvaluator()
context = FlowContext()
context.set("status", "active")
context.set("count", 42)

# Evaluate conditions
result = evaluator.evaluate(
    "context.data.status == 'active'",
    context
)
print(result)  # True

result = evaluator.evaluate(
    "context.data.count > 100",
    context
)
print(result)  # False
```

### Safety Validation

```python
evaluator = ConditionEvaluator()

# Check if safe
print(evaluator.is_safe("context.data.x == 1"))  # True
print(evaluator.is_safe("len(context.data.x)"))  # False

# Get validation errors
errors = evaluator.validate("import os")
print(errors)  # ["Import statements are not allowed"]
```

### AST Validation

```python
import ast
from flowengine import SafeASTValidator

# Parse expression
tree = ast.parse("x == 1 and y > 2", mode="eval")

# Validate
validator = SafeASTValidator()
is_safe = validator.validate(tree)
errors = validator.get_errors()

if not is_safe:
    print("Validation errors:", errors)
```

### Custom Evaluator with Engine

```python
from flowengine import FlowEngine, ConditionEvaluator

# Create custom evaluator
evaluator = ConditionEvaluator()

# Use with engine
engine = FlowEngine(config, components, evaluator=evaluator)
```
