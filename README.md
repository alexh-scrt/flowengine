# FlowEngine

**Lightweight YAML-driven workflow engine for Python — and an agent-native workflow IR**

FlowEngine enables developers to define execution flows declaratively in YAML, build pluggable component systems, and execute conditional branching based on runtime state. As of **v0.5.0** it is also a constrained **Agent Workflow IR**: AI agents (and [NeuroCore](https://github.com/alexh-scrt/neurocore)) can generate → validate → run → observe → repair flows, with machine-readable validation, capability metadata, a sandbox policy, flow-as-tool, and a CLI.

## Features

- **YAML-Driven Configuration** — Define flows in human-readable YAML files
- **Component-Based Architecture** — Build reusable, testable processing units
- **Graph-Based DAG Execution** — Define flows as directed acyclic graphs with topological ordering
- **Cyclic Graph Execution** — Build agentic loops with iteration limits and port-based exit conditions
- **Port-Based Output Routing** — Components route execution through named output ports
- **Conditional Execution** — Execute steps based on runtime context state
- **Async Component Support** — Native async processing with automatic sync fallback
- **Execution Checkpoints** — Suspend and resume flows mid-execution with serializable checkpoints
- **Step Lifecycle Hooks** — Observe flow execution with pluggable hook callbacks
- **Safe Expression Evaluation** — Condition expressions are validated against an AST allowlist
- **Full Type Hints** — Compatible with mypy strict mode
- **Execution Metadata** — Track timing, errors, and skipped components with step-level detail
- **Cooperative Timeout** — Protect against runaway flows with deadline-based timeouts
- **Component Registry** — Auto-instantiate components from type paths or validate types at runtime
- **Round-Trip Serialization** — Fully serialize and restore context state for replay/debugging
- **Minimal Dependencies** — Only requires `pyyaml` and `pydantic`

### Agent-Native (v0.5.0)

- **YAML as an Agent Workflow IR** — a constrained language agents generate safely instead of arbitrary Python
- **Machine-Readable Validation** — coded issues + JSON-patch repair hints (`FlowCompiler` → `CompileResult`)
- **Capability Metadata** — components declare inputs/outputs/ports/risk via `ComponentMeta`
- **Semantic Validation** — ports, reachability, cycle exits, terminal output, and input/output contract
- **Flow Contracts** — top-level `inputs`/`outputs` make a flow a callable worker
- **Sandbox Policy** — allow/deny lists, risk & approval gates, and resource caps (`ExecutionPolicy`)
- **Flow-as-Tool & Subflows** — call a whole flow as a tool (`FlowTool`) or nest one inside another (`SubflowComponent`)
- **Planning, Tracing, Replay** — dry-run plans, structured run traces, and deterministic replay
- **CLI** — `flowengine validate | plan | schema | normalize | apply-patch | components | template | run | replay`

## Installation

```bash
pip install flowengine
```

For HTTP component support:

```bash
pip install flowengine[http]
```

For development:

```bash
pip install flowengine[dev]
```

Installing FlowEngine also provides the `flowengine` command-line tool:

```bash
flowengine --help
flowengine validate flow.yaml --json
```

## Quick Start

### 1. Define a Component

```python
from flowengine import BaseComponent, FlowContext

class GreetComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.greeting = config.get("greeting", "Hello")

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("name", "World")
        context.set("message", f"{self.greeting}, {name}!")
        return context
```

### 2. Create a Flow Configuration

```yaml
# flow.yaml
name: "Greeting Flow"
version: "1.0"

components:
  - name: greeter
    type: myapp.GreetComponent
    config:
      greeting: "Hello"

flow:
  steps:
    - component: greeter
      description: "Generate greeting"
```

### 3. Execute the Flow

```python
from flowengine import ConfigLoader, FlowEngine, FlowContext

# Load configuration
config = ConfigLoader.load("flow.yaml")

# Create components
components = {"greeter": GreetComponent("greeter")}

# Create engine and execute
engine = FlowEngine(config, components)
context = FlowContext()
context.set("name", "FlowEngine")

result = engine.execute(context)
print(result.data.message)  # "Hello, FlowEngine!"
```

## Core Concepts

### Components

Components are the building blocks of flows. Each component has a lifecycle:

1. `__init__(name)` — Instance creation
2. `init(config)` — One-time configuration (called once)
3. `setup(context)` — Pre-processing (called each run)
4. `process(context)` — Main logic (called each run) **[required]**
5. `teardown(context)` — Cleanup (called each run)

```python
from flowengine import BaseComponent, FlowContext

class DatabaseComponent(BaseComponent):
    def init(self, config: dict) -> None:
        super().init(config)
        self.connection_string = config["connection_string"]
        self._conn = None

    def setup(self, context: FlowContext) -> None:
        self._conn = create_connection(self.connection_string)

    def process(self, context: FlowContext) -> FlowContext:
        data = self._conn.query("SELECT * FROM users")
        context.set("users", data)
        return context

    def teardown(self, context: FlowContext) -> None:
        if self._conn:
            self._conn.close()

    def validate_config(self) -> list[str]:
        errors = []
        if not self.config.get("connection_string"):
            errors.append("connection_string is required")
        return errors
```

### Context

The `FlowContext` carries data through the flow and tracks execution metadata:

```python
from flowengine import FlowContext

context = FlowContext()

# Set values
context.set("user", {"name": "Alice", "age": 30})

# Get values with dot notation
print(context.data.user.name)  # "Alice"

# Check for values
print(context.has("user"))  # True
print(context.get("missing", "default"))  # "default"

# Access metadata
print(context.metadata.flow_id)
print(context.metadata.component_timings)

# Serialize
print(context.to_json())
```

### Flow Configuration

```yaml
name: "My Flow"
version: "1.0"
description: "Optional description"

components:
  - name: component_name
    type: module.path.ComponentClass
    config:
      key: value

flow:
  type: sequential  # or "conditional" for first-match branching

  settings:
    fail_fast: true            # Stop on first error
    timeout_seconds: 300       # Max execution time (cooperative)
    on_condition_error: fail   # fail, skip, or warn

  steps:
    - component: component_name
      description: "What this step does"
      condition: "context.data.ready == True"
      on_error: fail  # fail, skip, or continue
```

### Settings Reference

| Setting | Default | Description |
|---------|---------|-------------|
| `fail_fast` | `true` | Stop on first component error |
| `timeout_seconds` | `300` | Maximum flow execution time in seconds |
| `timeout_mode` | `cooperative` | Timeout enforcement: `cooperative`, `hard_async`, `hard_process` |
| `require_deadline_check` | `false` | Require components to call `check_deadline()` in cooperative mode |
| `on_condition_error` | `fail` | How to handle invalid conditions: `fail` (raise exception), `skip` (skip step), `warn` (log and skip) |
| `max_iterations` | `10` | Maximum loop iterations for cyclic graphs |
| `on_max_iterations` | `"fail"` | Policy when max iterations reached: `fail`, `exit`, `warn` |

## Flow Types

FlowEngine supports three flow execution types:

### Sequential (Default)

Runs **all steps in order**. Each step's condition guards whether that individual step runs.

```yaml
flow:
  type: sequential  # default
  steps:
    - component: fetch_data      # Always runs
    - component: transform_data  # Runs if condition is True
      condition: "context.data.fetch_result.status == 'success'"
    - component: save_data       # Runs if condition is True
      condition: "context.data.transformed is not None"
    - component: notify_error    # Runs if condition is True
      condition: "context.data.fetch_result.status == 'error'"
```

All four steps are evaluated. Multiple steps can execute if their conditions match.

### Conditional (First-Match Branching)

**First-match branching** like a switch/case statement. Stops after the first step whose condition is True.

```yaml
flow:
  type: conditional  # first-match branching
  steps:
    - component: handle_user
      condition: "context.data.request_type == 'user'"
    - component: handle_order
      condition: "context.data.request_type == 'order'"
    - component: handle_admin
      condition: "context.data.request_type == 'admin'"
    - component: handle_unknown  # No condition = default case
```

Only **one step executes**. Once a condition matches, remaining steps are skipped.

### Graph (DAG Execution)

Define flows as **directed acyclic graphs** with topological ordering. Supports port-based routing for conditional branching.

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
      port: "valid"              # Only activates when port == "valid"
    - source: validate
      target: handle_invalid
      port: "invalid"            # Only activates when port == "invalid"
```

Nodes execute in topological order. Port-based edges enable conditional routing — components call `set_output_port(context, "valid")` to choose a branch.

### Cyclic Graph (Agent Loops) — v0.3.0

Define flows with **cycles** for iterative agent patterns. The graph executor automatically detects cycles and switches to a ready-queue BFS executor with iteration limits.

```yaml
flow:
  type: graph
  settings:
    max_iterations: 10          # Safety limit for loop iterations
    on_max_iterations: exit     # fail | exit | warn
  nodes:
    - id: plan
      component: planner
    - id: execute
      component: executor
    - id: evaluate
      component: evaluator
    - id: deliver
      component: deliverer
  edges:
    - source: plan
      target: execute
    - source: execute
      target: evaluate
    - source: evaluate
      target: plan
      port: "refine"            # Loop back when more work needed
    - source: evaluate
      target: deliver
      port: "done"              # Exit loop when quality threshold met
```

The evaluator component uses port-based routing to either loop back (`refine`) or exit to delivery (`done`):

```python
class EvaluateComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        quality = context.get("quality_score", 0)
        threshold = self.config.get("quality_threshold", 3)

        if quality >= threshold:
            self.set_output_port(context, "done")
        else:
            self.set_output_port(context, "refine")

        return context
```

After execution, cyclic metadata is available:

```python
result = engine.execute()
print(result.metadata.iteration_count)        # Number of loop iterations
print(result.metadata.node_visit_counts)      # Per-node execution counts
print(result.metadata.max_iterations_reached) # Whether limit was hit
```

| Setting | Default | Description |
|---------|---------|-------------|
| `max_iterations` | `10` | Maximum loop iterations before policy triggers |
| `on_max_iterations` | `"fail"` | `fail` (raise `MaxIterationsError`), `exit` (stop silently), `warn` (log + stop) |
| `max_visits` (per-node) | `None` | Cap individual node executions (defaults to `max_iterations`) |

| Flow Type | Behavior | Use Case |
|-----------|----------|----------|
| `sequential` | All matching steps run | Data pipelines, multi-step processing |
| `conditional` | First match wins, then stop | Request routing, dispatch, mutually exclusive branches |
| `graph` (DAG) | DAG with port-based routing | Complex workflows, approval flows |
| `graph` (cyclic) | Loops with iteration limits | Agent loops, iterative refinement, agentic AI patterns |

## Agent-Native API (v0.5.0)

FlowEngine YAML doubles as a constrained **Agent Workflow IR** — a language AI agents can generate, validate, run, observe, and repair, without writing arbitrary Python. The whole agent-facing API lives under `flowengine.agent` and is re-exported from the top-level package. All of it is **non-breaking**: existing flows and components work unchanged.

```
generate YAML → validate → (repair) → plan → run → observe trace → refine
```

### The compile → repair loop

`FlowCompiler.compile_yaml()` returns a structured `CompileResult` — never a raw exception — with coded, JSON-patchable issues so an agent can self-correct:

```python
from flowengine import FlowCompiler

result = FlowCompiler.compile_yaml(yaml_text, registry=my_registry)

if not result.valid:
    for issue in result.errors:
        print(issue.code, issue.path, issue.message, issue.suggestion)
        # issue.repair.yaml_patch is a list of RFC-6902 JSON Patch ops
else:
    engine = FlowEngine.from_config(result.flow_config)
```

Each `FlowIssue` carries a stable `IssueCode` (e.g. `UNKNOWN_COMPONENT`, `UNDECLARED_PORT`, `CYCLE_WITHOUT_EXIT`, `MISSING_INPUT_PRODUCER`), a document `path`, a "did you mean" `suggestion`, and an optional `repair` you can apply with `apply_patch()`.

### Component capability metadata

Components declare a machine-readable contract so agents can discover, validate, and safely compose them:

```python
from flowengine import BaseComponent, ComponentMeta, IOFieldSpec, PortSpec

class WebSearch(BaseComponent):
    meta = ComponentMeta(
        name="web_search",
        description="Searches the web and returns ranked results.",
        inputs={"query": IOFieldSpec(type="string", required=True)},
        outputs={"search_results": IOFieldSpec(type="array")},
        ports=[PortSpec(name="success"), PortSpec(name="no_results")],
        tags=["search", "web"],
        cost="low",
        effects=["read_web"],          # risk_level defaults to "low"
    )

    def process(self, context):
        context.set("search_results", do_search(context.get("query")))
        return context
```

Metadata is optional — components without it still work; semantic checks that need it simply degrade to warnings.

### Flow contracts (inputs / outputs)

Declare a flow's contract at the top level to make it a callable worker:

```yaml
name: research-worker
inputs:
  query: {type: string, required: true}
outputs:
  answer: {type: string}
  citations: {type: array}
components: [...]
flow: {...}
```

`validate_semantics()` then checks that declared outputs are produced, consumed keys have a producer or input, ports used by edges are declared, cycles have an exit, and the graph has a terminal path.

### Plan, trace, normalize, catalog, schema

```python
from flowengine import explain, AgentTrace, normalize_yaml, build_catalog, export_json_schema

plan = explain(config, registry)         # execution order, branches, cycles, required components, I/O
trace = AgentTrace.from_context(result)  # run_id, status, outputs, per-step records, errors
canonical = normalize_yaml(yaml_text)    # defaults filled, keys ordered, diff-friendly
catalog = build_catalog(registry)        # machine-readable component catalog
schema = export_json_schema("flow")      # JSON Schema for constrained generation
```

### Sandbox policy (risk & resource limits)

An agent may generate any YAML, but `ExecutionPolicy` decides what may run:

```python
from flowengine import ExecutionPolicy, FlowCompiler

policy = ExecutionPolicy(
    max_runtime_seconds=120,
    max_iterations=5,
    allowed_components=["web_search", "summarize", "final_answer"],
    denied_components=["shell_exec"],
    require_approval_for=["send_email", "execute_code"],
)

result = FlowCompiler.compile_yaml(yaml_text, registry=reg, policy=policy)  # violations are errors
safe_config = policy.apply_to_config(config)  # tighten timeout / max_iterations for runtime
```

### Flow-as-tool and subflows

Expose a whole flow as a callable tool, or nest one flow inside another:

```python
from flowengine import FlowTool

tool = FlowTool.from_yaml("research-worker.yaml")
schema = tool.tool_schema()          # JSON tool definition from the flow's inputs
result = tool.call(query="what is FlowEngine?")   # {"answer": ..., "citations": [...]}
```

```yaml
# Nested flow as a component
- name: literature_review
  type: flowengine.contrib.subflow.SubflowComponent
  config:
    path: ./subflows/literature-review.yaml
    inputs: {query: topic}        # parent 'query' -> child 'topic'
    outputs: [summary, citations]
```

### Deterministic replay

```python
from flowengine.agent.replay import RunRecord, InMemoryRunStore, replay

record = RunRecord.from_run(config, {"query": "..."}, result)
store = InMemoryRunStore(); store.save(record)
replayed = replay(record.run_id, store, from_node="critique")  # resume from a node
```

### Command-line interface

```bash
flowengine validate flow.yaml --json        # coded issues + repair hints
flowengine plan flow.yaml --json            # dry-run execution plan
flowengine schema --kind flow               # JSON Schema for constrained generation
flowengine normalize flow.yaml              # canonical YAML
flowengine apply-patch flow.yaml patch.json # apply JSON-patch repair
flowengine components --json                # component catalog
flowengine template list                    # canonical flow templates
flowengine template show plan-act-evaluate-loop
flowengine run flow.yaml --input-json '{"query":"..."}'   # run, print agent trace
flowengine replay run.json --from-node critique           # replay a saved run
```

Use `--policy policy.yaml` with `validate`/`run` to enforce a sandbox, and `--module pkg.mod` to make custom components discoverable.

### Templates & the agent prompt pack

Seven canonical templates (`sequential-task`, `graph-branching-task`, `plan-act-evaluate-loop`, `human-approval-task`, `map-reduce-research`, `tool-use-worker`, `supervisor-worker`) are available via `flowengine template`. A prompt pack for generating agents lives in [`docs/for-agents/`](docs/for-agents/): system prompt, YAML generation rules, error-repair guide, component selection, and safety policy.

### NeuroCore bridge

[NeuroCore](https://github.com/alexh-scrt/neurocore) skills are FlowEngine components. A skill's `SkillMeta` maps directly onto `ComponentMeta` (`provides → outputs`, `consumes → inputs`, plus tags/config_schema/requires_llm), so NeuroCore skills participate in FlowEngine's semantic validation, planning, and component catalog. Requires `flowengine>=0.5.0`.

## Conditional Step Execution

Steps can have conditions that are evaluated at runtime:

```yaml
steps:
  - component: fetch_data

  - component: process_data
    condition: "context.data.fetch_data.status == 'success'"

  - component: save_data
    condition: "context.data.process_data is not None"

  - component: notify_error
    condition: "context.data.fetch_data.status == 'error'"
```

### Allowed Expressions

Conditions support safe Python expressions:

| Category | Allowed |
|----------|---------|
| **Comparisons** | `<`, `>`, `<=`, `>=`, `==`, `!=` |
| **Logical** | `and`, `or`, `not` |
| **Identity** | `is`, `is not` |
| **Membership** | `in`, `not in` |
| **Attributes** | `context.data.user.name` |
| **Subscripts** | `context.data["key"]` |
| **Constants** | `True`, `False`, `None`, numbers, strings |

**Disallowed for security:**
- Function calls (`len()`, `print()`, etc.)
- Imports
- Lambda expressions
- List comprehensions

## Async Components

Components can implement native async processing:

```python
from flowengine import BaseComponent, FlowContext

class AsyncFetchComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        # Sync fallback
        return context

    async def process_async(self, context: FlowContext) -> FlowContext:
        data = await fetch_data_async()
        context.set("data", data)
        return context
```

The `is_async` property detects whether a component overrides `process_async`:

```python
comp = AsyncFetchComponent("fetch")
print(comp.is_async)  # True
```

## Execution Checkpoints (Suspend/Resume)

Flows can be suspended mid-execution and resumed later — useful for human-in-the-loop workflows:

```python
# Component suspends the flow
class ApprovalComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        if not context.has("resume_data"):
            context.suspend(self.name, reason="Needs human approval")
        else:
            decision = context.get("resume_data")
            context.set("approved", decision.get("approved", False))
        return context
```

```python
from flowengine.core.checkpoint import InMemoryCheckpointStore

store = InMemoryCheckpointStore()
engine = FlowEngine(config, components, checkpoint_store=store)

# Execute — flow suspends at approval node
result = engine.execute()
checkpoint_id = result.get("checkpoint_id")

# Later, resume with data
resumed = engine.resume(checkpoint_id, resume_data={"approved": True})
print(resumed.get("approved"))  # True
```

## Step Lifecycle Hooks

Observe flow execution with hooks:

```python
class LoggingHook:
    def on_node_start(self, node_id, component_name, context):
        print(f"Starting: {node_id}")

    def on_node_complete(self, node_id, component_name, context, duration):
        print(f"Completed: {node_id} in {duration:.3f}s")

    def on_node_error(self, node_id, component_name, error, context):
        print(f"Error in {node_id}: {error}")

    def on_node_skipped(self, node_id, component_name, reason):
        print(f"Skipped: {node_id} ({reason})")

    def on_flow_suspended(self, node_id, reason, checkpoint_id):
        print(f"Suspended at {node_id}: {reason}")

engine = FlowEngine(config, components, hooks=[LoggingHook()])
```

Hooks are fault-tolerant — a broken hook never interrupts flow execution.

## Error Handling

Configure error behavior per step:

```yaml
steps:
  - component: risky_operation
    on_error: continue  # Options: fail, skip, continue

  - component: cleanup
    # Always runs even if previous step failed (with on_error: continue)
```

Use `fail_fast: false` in settings to allow continuing after errors:

```yaml
flow:
  settings:
    fail_fast: false
  steps:
    - component: step1
      on_error: continue  # Log error, continue to next step
    - component: step2
      on_error: skip      # Log error, mark as skipped
    - component: step3
      on_error: fail      # Stop execution (default)
```

Access errors in context:

```python
result = engine.execute(context)

if result.metadata.has_errors:
    for error in result.metadata.errors:
        print(f"{error['component']}: {error['message']}")
```

## Timeout Handling

Flows can have a maximum execution time:

```yaml
flow:
  settings:
    timeout_seconds: 60  # 60 second limit
    timeout_mode: cooperative  # cooperative (default), hard_async, or hard_process
```

### Timeout Modes

FlowEngine supports three timeout enforcement modes:

| Mode | Enforcement | Use Case |
|------|-------------|----------|
| `cooperative` | Components call `check_deadline()` | Default, safest for complex components |
| `hard_async` | Uses `asyncio.wait_for` | I/O-bound components, async-friendly code |
| `hard_process` | Runs in separate process | CPU-bound components, guaranteed termination |

### Cooperative Mode (Default)

The engine sets a **deadline** before each step and checks between steps. Components cooperate by calling `check_deadline()`:

```python
class LongRunningComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        for item in large_dataset:
            self.check_deadline(context)  # Check periodically
            process_item(item)
        return context
```

**Strict Enforcement:** Enable `require_deadline_check: true` to raise an error when long-running components don't call `check_deadline()`:

```yaml
flow:
  settings:
    timeout_seconds: 60
    timeout_mode: cooperative
    require_deadline_check: true  # Raise error instead of warning
```

### Hard Async Mode

Uses `asyncio.wait_for` to enforce timeouts. Components run in a thread executor, allowing cancellation:

```yaml
flow:
  settings:
    timeout_seconds: 10
    timeout_mode: hard_async
```

**Guarantees:**
- Timeout is enforced even if component doesn't call `check_deadline()`
- Teardown always runs (in main thread)
- Best for I/O-bound operations

### Hard Process Mode

Runs each step in a separate process with a hard kill on timeout:

```yaml
flow:
  settings:
    timeout_seconds: 30
    timeout_mode: hard_process
```

**Guarantees:**
- Component is forcibly terminated on timeout
- Teardown always runs in main process
- Context is serialized/deserialized across process boundary
- Best for CPU-bound operations that may hang

**Requirements:**
- Components must be picklable (standard Python classes)
- Context data must be JSON-serializable

### Timeout Guarantees by Mode

| Scenario | Cooperative | Hard Async | Hard Process |
|----------|-------------|------------|--------------|
| Between steps | ✅ Always | ✅ Always | ✅ Always |
| Component calls `check_deadline()` | ✅ Yes | ✅ Yes | ✅ Yes |
| Component blocks without checking | ❌ Runs until returns | ✅ Cancelled | ✅ Killed |
| Teardown runs on timeout | ✅ Yes | ✅ Yes | ✅ Yes |

### Choosing a Timeout Mode

```
┌─────────────────────────────────────────────────────────────┐
│                    Choose Timeout Mode                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Components call check_deadline()?                          │
│    └── YES → Use cooperative (default, safest)              │
│    └── NO  → Components do I/O operations?                  │
│                └── YES → Use hard_async                     │
│                └── NO  → Components are CPU-bound?          │
│                            └── YES → Use hard_process       │
│                            └── NO  → Use cooperative        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Error Handling

```python
from flowengine import FlowTimeoutError, DeadlineCheckError

try:
    result = engine.execute()
except FlowTimeoutError as e:
    print(f"Timed out after {e.elapsed:.2f}s (limit: {e.timeout}s)")
except DeadlineCheckError as e:
    print(f"Component '{e.component}' didn't call check_deadline()")
```

### Best Practices for Timeout Compliance

1. **Cooperative mode:** Call `self.check_deadline(context)` in loops and before I/O
2. **Hard async:** Keep components stateless when possible
3. **Hard process:** Ensure context data is JSON-serializable
4. **All modes:** Implement proper `teardown()` for cleanup

## Component Registry

For YAML-complete flows, you can auto-instantiate components from their type paths:

```python
from flowengine import ConfigLoader, FlowEngine

# Load config and create engine with auto-instantiation
config = ConfigLoader.load("flow.yaml")
engine = FlowEngine.from_config(config)

result = engine.execute()
```

Or use the registry directly:

```python
from flowengine import ComponentRegistry, FlowEngine

registry = ComponentRegistry()
registry.register_class("greeter", GreetComponent)

# Registry is used when creating engine
engine = FlowEngine.from_config(config, registry=registry)
```

Validate that provided components match their declared types:

```python
engine = FlowEngine(config, components)
errors = engine.validate_component_types()
if errors:
    print("Type mismatches:", errors)
```

## Step Timing Details

Execution metadata tracks timing per step, even for repeated components:

```python
result = engine.execute()

# Individual step timings (preserves order)
for timing in result.metadata.step_timings:
    print(f"Step {timing.step_index}: {timing.component} took {timing.duration:.3f}s")

# Aggregated by component (backward-compatible)
for name, total in result.metadata.component_timings.items():
    print(f"{name}: {total:.3f}s total")
```

## Context Serialization

Contexts can be fully serialized and restored:

```python
from flowengine import FlowContext

# After execution
result = engine.execute()

# Serialize to JSON
json_str = result.to_json()

# Later, restore the context
restored = FlowContext.from_json(json_str)

# All data preserved
print(restored.get("key"))
print(restored.metadata.flow_id)
print(restored.metadata.step_timings)
```

## Contrib Components

### LoggingComponent

Logs context state for debugging:

```yaml
- name: debug
  type: flowengine.contrib.logging.LoggingComponent
  config:
    level: debug  # debug, info, warning, error
    message: "Current state"
    log_data: true
    log_metadata: false
    keys:  # Optional: only log specific keys
      - user
      - result
```

### HTTPComponent

Makes HTTP requests (requires `pip install flowengine[http]`):

```yaml
- name: api
  type: flowengine.contrib.http.HTTPComponent
  config:
    base_url: "https://api.example.com"
    timeout: 30
    headers:
      Authorization: "Bearer token"
    method: GET  # GET, POST, PUT, PATCH, DELETE
```

Usage:

```python
context.set("endpoint", "/users/123")
result = engine.execute(context)
print(result.data.api.data)  # Response JSON
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `BaseComponent` | Abstract base class for components |
| `FlowContext` | Context passed through all components |
| `DotDict` | Dictionary with attribute-style access |
| `ExecutionMetadata` | Tracks timing, errors, and execution state |
| `StepTiming` | Timing info for a single step execution |
| `FlowEngine` | Orchestrates flow execution |
| `GraphExecutor` | DAG-based graph flow executor |
| `ExecutionHook` | Protocol for step lifecycle hooks |
| `Checkpoint` | Serializable flow execution snapshot |
| `CheckpointStore` | Abstract base class for checkpoint persistence |
| `InMemoryCheckpointStore` | In-memory checkpoint store implementation |

### Configuration Classes

| Class | Description |
|-------|-------------|
| `ConfigLoader` | Loads YAML configurations |
| `FlowConfig` | Complete flow configuration model |
| `ComponentConfig` | Component configuration model |
| `StepConfig` | Step configuration model |
| `FlowSettings` | Execution settings model |
| `FlowDefinition` | Flow structure and execution definition |
| `GraphNodeConfig` | Node configuration for graph flows |
| `GraphEdgeConfig` | Edge configuration for graph flows |
| `ComponentRegistry` | Registry for dynamic component loading |

### Agent-Native Classes (v0.5.0)

| Class / Function | Description |
|------------------|-------------|
| `FlowCompiler` / `CompileResult` | Compile YAML → structured verdict for the agent repair loop |
| `FlowIssue` / `IssueCode` | Coded, machine-matchable validation finding |
| `RepairSuggestion` / `JsonPatchOp` | Structured, applicable repair (RFC-6902 JSON Patch) |
| `apply_patch()` | Minimal JSON Patch applier |
| `validate_semantics()` | Semantic checks beyond schema |
| `ComponentMeta` / `IOFieldSpec` / `PortSpec` | Component capability manifest + contract types |
| `explain()` / `FlowPlan` | Dry-run execution plan |
| `AgentTrace` | Structured, LLM-friendly run trace |
| `normalize_yaml()` | Canonical YAML rendering |
| `build_catalog()` | Machine-readable component catalog |
| `export_json_schema()` | JSON Schema export for constrained generation |
| `ExecutionPolicy` | Sandbox policy (allow/deny, risk, approval, resource caps) |
| `FlowTool` | Expose a flow as a callable, schema-bearing tool |
| `SubflowComponent` | Run a nested flow as a component |
| `RunRecord` / `RunStore` / `replay()` | Deterministic run capture and replay |
| `list_templates()` / `get_template()` | Canonical flow templates |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `FlowEngineError` | Base exception for all errors |
| `ConfigurationError` | Invalid configuration |
| `FlowExecutionError` | Runtime execution error |
| `FlowTimeoutError` | Flow exceeded timeout_seconds |
| `MaxIterationsError` | Cyclic graph exceeded max_iterations (with on_max_iterations=fail) |
| `DeadlineCheckError` | Component didn't call check_deadline() (with require_deadline_check=True) |
| `PolicyViolationError` | Flow violated an `ExecutionPolicy` |
| `ComponentError` | Component processing error |
| `ConditionEvaluationError` | Invalid/unsafe condition |

## Examples

See the `examples/` directory for complete examples:

- `simple_flow.py` — Basic flow execution
- `conditional_flow.py` — Sequential flow with conditional steps
- `routing_flow.py` — Conditional flow with first-match branching
- `timeout_modes.py` — Timeout enforcement modes (cooperative, hard_async, hard_process)
- `custom_components.py` — Advanced component patterns
- `agent_loop.py` — Cyclic graph agent loop with iterative refinement (v0.3.0)

Run examples:

```bash
cd examples
python simple_flow.py
python conditional_flow.py
python routing_flow.py
python timeout_modes.py
python custom_components.py
python agent_loop.py
```

## Development

### Setup

```bash
git clone https://github.com/yourorg/flowengine.git
cd flowengine
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest tests/ -v --cov=flowengine
```

### Type Checking

```bash
mypy src/flowengine
```

### Linting

```bash
ruff check src/ tests/
```

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request
