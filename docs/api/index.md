# API Reference

Complete API documentation for FlowEngine. All public classes, methods, and functions are documented here.

---

## Module Structure

```
flowengine/
├── core/              # Core execution engine
│   ├── engine.py      # FlowEngine class
│   ├── component.py   # BaseComponent abstract class
│   └── context.py     # FlowContext, DotDict, ExecutionMetadata
├── config/            # Configuration and validation
│   ├── loader.py      # ConfigLoader class
│   ├── schema.py      # Pydantic models (FlowConfig, etc.)
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
| [Core](core.md) | `FlowEngine`, `BaseComponent`, `FlowContext`, `DotDict`, `ExecutionMetadata` |
| [Configuration](config.md) | `ConfigLoader`, `FlowConfig`, `ComponentConfig`, `StepConfig`, `FlowSettings` |
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

# Component lifecycle
BaseComponent.process(context: FlowContext) -> FlowContext
BaseComponent.init(config: dict[str, Any]) -> None
BaseComponent.validate_config() -> list[str]

# Configuration
ConfigLoader.load(path: Union[str, Path]) -> FlowConfig
FlowEngine.from_config(
    config: FlowConfig,
    evaluator: Optional[ConditionEvaluator] = None,
    registry: Optional[ComponentRegistry] = None
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
```

---

## Version

```python
import flowengine
print(flowengine.__version__)
```
