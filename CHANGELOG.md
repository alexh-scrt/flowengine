# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-02-27

### Added

- **Cyclic Graph Execution** (`max_iterations` + ready-queue BFS)
  - Graphs with cycles are now executed via a ready-queue BFS executor
  - Cycle detection via DFS with white/gray/black coloring identifies back-edges
  - Iteration counting at back-edge targets with configurable `max_iterations` limit
  - Three `on_max_iterations` policies: `fail` (raise `MaxIterationsError`), `exit` (silent stop), `warn` (log + stop)
  - Per-node `max_visits` limit to cap individual node executions
  - DAG fast path preserved untouched — zero behavioral change for acyclic graphs

- **`MaxIterationsError` Exception**
  - New exception with `max_iterations`, `actual_iterations`, and `cycle_entry_node` attributes
  - Raised when `on_max_iterations: fail` and the iteration limit is reached

- **Cyclic Execution Metadata**
  - `ExecutionMetadata.node_visit_counts`: per-node visit tracking (source of truth for cyclic flows)
  - `ExecutionMetadata.iteration_count`: total iteration count across all cycles
  - `ExecutionMetadata.max_iterations_reached`: flag indicating whether the limit was hit
  - Full round-trip serialization of cyclic state via `to_dict()`/`from_dict()`

- **Execution Hooks for Cycles**
  - `on_iteration_start(iteration, context)`: called at each iteration boundary
  - `on_iteration_complete(iteration, context)`: called after each iteration completes
  - `on_max_iterations(iteration, policy, context)`: called when max iterations is reached

- **Checkpoint/Resume in Cyclic Flows**
  - Suspend and resume works within cyclic execution paths
  - Visit counts and iteration state preserved across checkpoint boundaries

- **New Flow Settings**
  - `max_iterations` (default: 10): maximum iteration count for cyclic graphs
  - `on_max_iterations` (default: `"fail"`): policy when limit is reached
  - `max_visits` on `GraphNodeConfig`: per-node visit cap

- **Agent Loop Example** (`examples/agent_loop.py`)
  - Runnable example demonstrating `plan → execute → observe → evaluate → [refine|deliver]`
  - YAML configuration in `examples/flows/agent_loop.yaml`

### Changed

- `GraphExecutor.execute()` now dispatches to `_execute_dag()` or `_execute_cyclic()` based on cycle detection
- Previous `execute()` renamed to `_execute_dag()` (no behavioral change for DAG flows)
- Shared `_execute_node()` method extracted for both DAG and cyclic paths
- Cycle-participating nodes are NOT added to `completed_nodes` (only terminal/non-cycle nodes are)
- `FlowEngine.dry_run()` returns all components for cyclic graphs instead of topological sort

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