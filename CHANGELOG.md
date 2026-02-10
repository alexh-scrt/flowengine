# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2025-02-10

### Added

- **Graph-Based DAG Execution** (`flow.type: "graph"`)
  - Topological ordering via Kahn's algorithm
  - `GraphNodeConfig` and `GraphEdgeConfig` schema models
  - `GraphExecutor` class in `core/graph.py`
  - Cycle detection with clear error messages

- **Port-Based Output Routing**
  - Components can signal an active output port via `set_output_port(context, port)`
  - Graph edges with `port` field route conditionally based on active port
  - `FlowContext.set_port()`, `get_active_port()`, `clear_port()` methods
  - Unconditional edges (no port) always activate

- **Async Component Support**
  - `BaseComponent.process_async()` with automatic sync fallback
  - `BaseComponent.is_async` property for detection
  - Full async lifecycle support

- **Execution Checkpoints (Suspend/Resume)**
  - `FlowContext.suspend(node_id, reason)` for pausing flows mid-execution
  - `Checkpoint` dataclass with full JSON serialization
  - `CheckpointStore` abstract base class with `InMemoryCheckpointStore` implementation
  - `FlowEngine.resume(checkpoint_id, resume_data)` for continuing suspended flows
  - Suspended nodes re-execute on resume (not skipped)

- **Step Lifecycle Hooks**
  - `ExecutionHook` Protocol with five hook points:
    `on_node_start`, `on_node_complete`, `on_node_error`, `on_node_skipped`, `on_flow_suspended`
  - Hooks are fault-tolerant — broken hooks don't break flow execution
  - Multiple hooks supported simultaneously

- **Enhanced FlowDefinition Validation**
  - `model_validator` ensures correct fields for each flow type
  - Graph-specific validation: unique node IDs, valid edge references
  - Backward-compatible: `steps` remains for sequential/conditional flows

### Changed

- `FlowEngine.__init__` accepts optional `checkpoint_store` and `hooks` parameters
- `FlowEngine.from_config` accepts optional `checkpoint_store` and `hooks` parameters
- `FlowDefinition.type` now accepts `"graph"` in addition to `"sequential"` and `"conditional"`
- `FlowDefinition.steps` is now optional (not required for graph flows)
- `ExecutionMetadata` includes `suspended`, `suspended_at_node`, `suspension_reason`, `completed_nodes` fields
- Context serialization includes suspension and completed_nodes state

## [0.1.0] - 2024-12-28

### Added

- Initial release
- `BaseComponent` abstract base class with lifecycle methods
- `FlowContext` data container with attribute-style access
- `DotDict` helper for nested dictionary access
- `FlowEngine` executor for running component flows
- `ConfigLoader` for loading YAML configurations
- Pydantic schemas for configuration validation
- `ConditionEvaluator` for safe expression evaluation
- `SafeASTValidator` for security validation
- Custom exception hierarchy
- Comprehensive test suite
- Documentation and examples

### Security

- Safe expression evaluation prevents code injection
- Restricted AST nodes prevent malicious code execution
- No access to Python builtins in condition evaluation

## [0.1.1] - 2025-12-28

### Added

- Documentation and examples https://flowengine.readthedocs.io