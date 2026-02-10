# API Reference

Complete API documentation for FlowEngine. All public classes, methods, and functions are documented here.

---

## Module Structure

```
flowengine/
├── core/              # Core execution engine
│   ├── engine.py      # FlowEngine, ExecutionHook
│   ├── component.py   # BaseComponent abstract class
│   ├── context.py     # FlowContext, DotDict, ExecutionMetadata
│   ├── graph.py       # GraphExecutor (DAG execution)
│   └── checkpoint.py  # Checkpoint, CheckpointStore, InMemoryCheckpointStore
├── config/            # Configuration and validation
│   ├── loader.py      # ConfigLoader class
│   ├── schema.py      # Pydantic models (FlowConfig, GraphNodeConfig, etc.)
│   └── registry.py    # ComponentRegistry
├── eval/              # Expression evaluation
│   ├── evaluator.py   # ConditionEvaluator class
│   └── safe_ast.py    # SafeASTValidator class
├── contrib/           # Ready-to-use components
│   ├── logging.py     # LoggingComponent
│   └── http.py        # HTTPComponent
└── errors/            # Exception hierarchy
    └── exceptions.py  # All custom exceptions
```

---

## Quick Import Guide

### Essential Imports

```python
from flowengine import (
    # Core classes
    BaseComponent,
    FlowContext,
    FlowEngine,

    # Configuration
    ConfigLoader,
    FlowConfig,

    # Contrib components
    LoggingComponent,
)
```

### Configuration Classes

```python
from flowengine import (
    FlowConfig,
    ComponentConfig,
    StepConfig,
    FlowSettings,
    FlowDefinition,
    GraphNodeConfig,
    GraphEdgeConfig,
)
```

### Graph Execution and Hooks

```python
from flowengine import (
    # Graph executor
    GraphExecutor,
    ExecutionHook,

    # Checkpoints
    Checkpoint,
    CheckpointStore,
    InMemoryCheckpointStore,
)
```

### Advanced Usage

```python
from flowengine import (
    # Registry
    ComponentRegistry,
    load_component_class,

    # Evaluation
    ConditionEvaluator,
    SafeASTValidator,

    # Context internals
    DotDict,
    ExecutionMetadata,
    StepTiming,
)
```

### Exception Handling

```python
from flowengine import (
    FlowEngineError,
    ConfigurationError,
    FlowExecutionError,
    FlowTimeoutError,
    DeadlineCheckError,
    ComponentError,
    ConditionEvaluationError,
)
```

---

## API Sections

| Section | Description |
|---------|-------------|
| [Core](core.md) | `FlowEngine`, `BaseComponent`, `FlowContext`, `GraphExecutor`, `ExecutionHook`, `Checkpoint`, `CheckpointStore` |
| [Configuration](config.md) | `ConfigLoader`, `FlowConfig`, `ComponentConfig`, `StepConfig`, `FlowSettings`, `GraphNodeConfig`, `GraphEdgeConfig` |
| [Registry](registry.md) | `ComponentRegistry`, `load_component_class`, `validate_component_type` |
| [Evaluation](eval.md) | `ConditionEvaluator`, `SafeASTValidator` |
| [Errors](errors.md) | Exception hierarchy and attributes |
| [Contrib](contrib.md) | `LoggingComponent`, `HTTPComponent` |

---

## Type Annotations

FlowEngine is fully typed and compatible with mypy strict mode. Key type signatures:

```python
# Core execution
FlowEngine.execute(
    context: Optional[FlowContext] = None,
    input_data: Any = None
) -> FlowContext

FlowEngine.resume(
    checkpoint_id: str,
    resume_data: Any = None
) -> FlowContext

# Component lifecycle
BaseComponent.process(context: FlowContext) -> FlowContext
BaseComponent.process_async(context: FlowContext) -> FlowContext  # async
BaseComponent.init(config: dict[str, Any]) -> None
BaseComponent.validate_config() -> list[str]
BaseComponent.set_output_port(context: FlowContext, port: str) -> None
BaseComponent.is_async -> bool  # property

# Context port/suspension
FlowContext.set_port(port: str) -> None
FlowContext.get_active_port() -> Optional[str]
FlowContext.clear_port() -> None
FlowContext.suspend(node_id: str, reason: str = "") -> None

# Configuration
ConfigLoader.load(path: Union[str, Path]) -> FlowConfig
FlowEngine.from_config(
    config: FlowConfig,
    evaluator: Optional[ConditionEvaluator] = None,
    registry: Optional[ComponentRegistry] = None,
    checkpoint_store: Optional[CheckpointStore] = None,
    hooks: Optional[list[Any]] = None
) -> FlowEngine

# Condition evaluation
ConditionEvaluator.evaluate(
    condition: str,
    context: FlowContext
) -> bool

# Registry
ComponentRegistry.create_from_path(
    type_path: str,
    instance_name: str
) -> BaseComponent

# Checkpoints
Checkpoint.to_dict() -> dict[str, Any]
Checkpoint.from_dict(data: dict[str, Any]) -> Checkpoint
CheckpointStore.save(checkpoint: Checkpoint) -> str
CheckpointStore.load(checkpoint_id: str) -> Optional[Checkpoint]
CheckpointStore.delete(checkpoint_id: str) -> None
```

---

## Version

```python
import flowengine
print(flowengine.__version__)
```
