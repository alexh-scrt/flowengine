# Architecture

An overview of FlowEngine's internal design and architecture decisions.

---

## Design Principles

### 1. Separation of Concerns

- **Configuration**: YAML defines flow structure
- **Components**: Python classes contain business logic
- **Engine**: Orchestrates execution
- **Context**: Carries data between components

### 2. Declarative Over Imperative

Flow logic is declared in YAML, not coded:

```yaml
# Declarative - what should happen
flow:
  steps:
    - component: fetch
    - component: process
      condition: "context.data.fetch_status == 'success'"
```

Not:

```python
# Imperative - how to do it
if fetch_result.status == "success":
    process(data)
```

### 3. Safety First

- Condition expressions are AST-validated
- No function calls in conditions
- No imports or code execution

### 4. Observable by Default

- All step timings tracked
- Errors collected in metadata
- Skipped components recorded

---

## Module Structure

```
src/flowengine/
├── __init__.py          # Public API exports
├── core/
│   ├── __init__.py
│   ├── engine.py        # FlowEngine - main orchestrator
│   ├── component.py     # BaseComponent - abstract base
│   └── context.py       # FlowContext, DotDict, metadata
├── config/
│   ├── __init__.py
│   ├── loader.py        # ConfigLoader - YAML parsing
│   ├── schema.py        # Pydantic models for validation
│   └── registry.py      # ComponentRegistry - dynamic loading
├── eval/
│   ├── __init__.py
│   ├── evaluator.py     # ConditionEvaluator
│   └── safe_ast.py      # SafeASTValidator
├── errors/
│   ├── __init__.py
│   └── exceptions.py    # Exception hierarchy
└── contrib/
    ├── __init__.py
    ├── logging.py       # LoggingComponent
    └── http.py          # HTTPComponent
```

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         FlowEngine.execute()                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Initialize Context                                          │
│     └── Create FlowContext with metadata                        │
│                                                                 │
│  2. Set Deadline                                                │
│     └── Calculate deadline from timeout_seconds                 │
│                                                                 │
│  3. For each step in config.steps:                              │
│     │                                                           │
│     ├── Check deadline (between steps)                          │
│     │                                                           │
│     ├── Evaluate condition (if present)                         │
│     │   └── ConditionEvaluator.evaluate()                       │
│     │                                                           │
│     ├── If condition False:                                     │
│     │   └── Record as skipped, continue                         │
│     │                                                           │
│     ├── If condition True (or no condition):                    │
│     │   │                                                       │
│     │   ├── component.setup(context)                            │
│     │   │                                                       │
│     │   ├── component.process(context) ─────────────────────┐   │
│     │   │   │                                               │   │
│     │   │   │  ┌─────────────────────────────────────────┐  │   │
│     │   │   │  │ Timeout Mode                            │  │   │
│     │   │   │  ├─────────────────────────────────────────┤  │   │
│     │   │   │  │ cooperative: run in main thread         │  │   │
│     │   │   │  │ hard_async:  run in thread executor     │  │   │
│     │   │   │  │ hard_process: run in separate process   │  │   │
│     │   │   │  └─────────────────────────────────────────┘  │   │
│     │   │   │                                               │   │
│     │   │   └───────────────────────────────────────────────┘   │
│     │   │                                                       │
│     │   ├── component.teardown(context) (always runs)           │
│     │   │                                                       │
│     │   └── Record timing                                       │
│     │                                                           │
│     └── Handle errors based on on_error setting                 │
│                                                                 │
│  4. Return context with all results and metadata                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow Types

### Sequential Flow

All steps evaluated, matching conditions execute:

```
Step 1 ──┬── condition? ──┬── True  → Execute
         │                └── False → Skip
         ↓
Step 2 ──┬── condition? ──┬── True  → Execute
         │                └── False → Skip
         ↓
Step 3 ──┬── condition? ──┬── True  → Execute
         │                └── False → Skip
         ↓
        ...
```

### Conditional Flow

First matching condition wins, then stop:

```
Step 1 ──┬── condition? ──┬── True  → Execute → STOP
         │                └── False → Continue
         ↓
Step 2 ──┬── condition? ──┬── True  → Execute → STOP
         │                └── False → Continue
         ↓
Step 3 ──┬── condition? ──┬── True  → Execute → STOP
         │                └── False → Continue
         ↓
Step 4 ── (no condition) ──────────→ Execute (default) → STOP
```

---

## Timeout Modes

### Cooperative

```
┌─────────────────────────────────────┐
│          Main Thread                │
├─────────────────────────────────────┤
│                                     │
│  deadline = now + timeout           │
│            │                        │
│            ↓                        │
│  ┌─────────────────────────────┐    │
│  │ component.process(context)  │    │
│  │                             │    │
│  │   self.check_deadline() ───────→ if now > deadline:
│  │   ...                       │       raise FlowTimeoutError
│  │   self.check_deadline() ───────→ if now > deadline:
│  │   ...                       │       raise FlowTimeoutError
│  └─────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

### Hard Async

```
┌─────────────────────────────────────┐
│          Main Thread                │
├─────────────────────────────────────┤
│                                     │
│  asyncio.wait_for(                  │
│    run_in_executor(                 │
│      component.process             │
│    ),                               │
│    timeout=remaining_time           │
│  )                                  │
│            │                        │
│            ↓                        │
│  ┌─────────────────────────────┐    │
│  │ Thread Pool Executor        │    │
│  │ ─────────────────────────── │    │
│  │ component.process(context)  │    │
│  └─────────────────────────────┘    │
│            │                        │
│            ↓                        │
│  On timeout: CancelledError         │
│                                     │
└─────────────────────────────────────┘
```

### Hard Process

```
┌─────────────────────────────────────┐
│          Main Process               │
├─────────────────────────────────────┤
│                                     │
│  future = executor.submit(          │
│    run_in_process,                  │
│    component, context               │
│  )                                  │
│            │                        │
│            ↓                        │
│                    ┌────────────────────────────┐
│                    │      Child Process         │
│                    ├────────────────────────────┤
│                    │                            │
│  future.result(    │ component.process(context) │
│    timeout=remaining                            │
│  )                 │                            │
│            ↑       └────────────────────────────┘
│            │                        │
│  On timeout: terminate process      │
│  Teardown runs in main process      │
│                                     │
└─────────────────────────────────────┘
```

---

## Condition Evaluation

```
┌─────────────────────────────────────────────────────────────┐
│                 ConditionEvaluator.evaluate()               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Parse expression                                        │
│     └── ast.parse(condition, mode='eval')                   │
│                                                             │
│  2. Validate AST                                            │
│     └── SafeASTValidator.validate(tree)                     │
│         │                                                   │
│         ├── Allowed: Compare, BoolOp, Attribute, Subscript  │
│         │            Name, Constant, List, Tuple, Dict      │
│         │                                                   │
│         └── Disallowed: Call, Import, Lambda, Assign, etc.  │
│                                                             │
│  3. Compile                                                 │
│     └── compile(tree, '<condition>', 'eval')                │
│                                                             │
│  4. Evaluate with restricted namespace                      │
│     └── eval(code, {"context": context})                    │
│                                                             │
│  5. Return boolean result                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   FlowContext                                               │
│   ┌───────────────────────────────────────────────────┐     │
│   │                                                   │     │
│   │  data: DotDict                                    │     │
│   │  ┌───────────────────────────────────────────┐    │     │
│   │  │ user: {name: "Alice", id: 123}            │    │     │
│   │  │ fetch_result: {status: "success", ...}    │    │     │
│   │  │ processed_data: [...]                     │    │     │
│   │  └───────────────────────────────────────────┘    │     │
│   │                                                   │     │
│   │  metadata: ExecutionMetadata                      │     │
│   │  ┌───────────────────────────────────────────┐    │     │
│   │  │ flow_id: "abc-123"                        │    │     │
│   │  │ step_timings: [...]                       │    │     │
│   │  │ errors: [...]                             │    │     │
│   │  │ skipped_components: [...]                 │    │     │
│   │  └───────────────────────────────────────────┘    │     │
│   │                                                   │     │
│   │  input: Any (original input)                      │     │
│   │                                                   │     │
│   └───────────────────────────────────────────────────┘     │
│                                                             │
│        │                    │                    │          │
│        ↓                    ↓                    ↓          │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐       │
│   │ Comp 1  │ ──────→ │ Comp 2  │ ──────→ │ Comp 3  │       │
│   └─────────┘         └─────────┘         └─────────┘       │
│        │                    │                    │          │
│        ↓                    ↓                    ↓          │
│   context.set()        context.set()        context.set()   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   Component Execution                                       │
│   ┌───────────────────────────────────────────────────┐     │
│   │                                                   │     │
│   │   try:                                            │     │
│   │       setup()                                     │     │
│   │       process()                                   │     │
│   │   except Exception:                               │     │
│   │       │                                           │     │
│   │       ↓                                           │     │
│   │   ┌───────────────────────────────────────────┐   │     │
│   │   │ on_error setting                          │   │     │
│   │   ├───────────────────────────────────────────┤   │     │
│   │   │ "fail"     → raise immediately            │   │     │
│   │   │ "skip"     → mark skipped, continue       │   │     │
│   │   │ "continue" → record error, continue       │   │     │
│   │   └───────────────────────────────────────────┘   │     │
│   │                                                   │     │
│   │   finally:                                        │     │
│   │       teardown() (always runs)                    │     │
│   │                                                   │     │
│   └───────────────────────────────────────────────────┘     │
│                                                             │
│   ┌───────────────────────────────────────────────────┐     │
│   │ fail_fast setting                                 │     │
│   ├───────────────────────────────────────────────────┤     │
│   │ true  → stop on first error                       │     │
│   │ false → collect errors, continue                  │     │
│   └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependencies

FlowEngine has minimal dependencies:

| Package | Purpose |
|---------|---------|
| `pyyaml` | YAML parsing |
| `pydantic` | Schema validation |

Optional:

| Package | Purpose |
|---------|---------|
| `httpx` | HTTPComponent |

---

## Extension Points

### Custom Components

Extend `BaseComponent`:

```python
class MyComponent(BaseComponent):
    def process(self, context):
        ...
```

### Custom Evaluator

Replace condition evaluation:

```python
engine = FlowEngine(config, components, evaluator=MyEvaluator())
```

### Custom Registry

Plug in component discovery:

```python
engine = FlowEngine.from_config(config, registry=MyRegistry())
```

---

## Next Steps

- [Component Registry](component-registry.md) - Dynamic loading
- [Serialization](serialization.md) - Context serialization
- [API Reference](../api/index.md) - Full API documentation
