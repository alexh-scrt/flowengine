# Core Module

The core module contains the main classes for flow execution.

---

## FlowEngine

The main orchestrator for executing flows.

::: flowengine.core.engine.FlowEngine
    options:
      show_source: false
      members:
        - __init__
        - execute
        - resume
        - validate
        - dry_run
        - validate_component_types
        - from_config

---

## BaseComponent

Abstract base class for all components.

::: flowengine.core.component.BaseComponent
    options:
      show_source: false
      members:
        - __init__
        - init
        - setup
        - process
        - process_async
        - teardown
        - validate_config
        - health_check
        - check_deadline
        - set_output_port
        - name
        - config
        - is_initialized
        - is_async

---

## FlowContext

Context object passed through all components.

::: flowengine.core.context.FlowContext
    options:
      show_source: false
      members:
        - __init__
        - set
        - get
        - has
        - delete
        - set_port
        - get_active_port
        - clear_port
        - suspend
        - to_dict
        - to_json
        - from_dict
        - from_json
        - copy
        - data
        - metadata
        - input

---

## DotDict

Dictionary with attribute-style access.

::: flowengine.core.context.DotDict
    options:
      show_source: false
      members:
        - __init__
        - get
        - keys
        - values
        - items
        - update
        - to_dict

---

## ExecutionMetadata

Tracks timing, errors, and execution state.

::: flowengine.core.context.ExecutionMetadata
    options:
      show_source: false
      members:
        - __init__
        - flow_id
        - started_at
        - completed_at
        - step_timings
        - skipped_components
        - errors
        - condition_errors
        - add_error
        - add_condition_error
        - record_timing
        - component_timings
        - has_errors
        - has_condition_errors
        - total_duration
        - suspended
        - suspended_at_node
        - suspension_reason
        - completed_nodes

---

## StepTiming

Timing information for a single step execution.

::: flowengine.core.context.StepTiming
    options:
      show_source: false
      members:
        - step_index
        - component
        - duration
        - started_at
        - execution_order

---

## GraphExecutor

Executes graph-type flows using topological ordering with port-based routing.

::: flowengine.core.graph.GraphExecutor
    options:
      show_source: false
      members:
        - __init__
        - execute

---

## ExecutionHook

Protocol for step lifecycle hooks. Implement any or all methods.

::: flowengine.core.engine.ExecutionHook
    options:
      show_source: false
      members:
        - on_node_start
        - on_node_complete
        - on_node_error
        - on_node_skipped
        - on_flow_suspended

---

## Checkpoint

Serializable snapshot of flow execution state for suspend/resume.

::: flowengine.core.checkpoint.Checkpoint
    options:
      show_source: false
      members:
        - __init__
        - checkpoint_id
        - flow_config
        - context
        - created_at
        - to_dict
        - from_dict
        - to_json
        - from_json

---

## CheckpointStore

Abstract base class for checkpoint persistence.

::: flowengine.core.checkpoint.CheckpointStore
    options:
      show_source: false
      members:
        - save
        - load
        - delete

---

## InMemoryCheckpointStore

In-memory implementation of `CheckpointStore`.

::: flowengine.core.checkpoint.InMemoryCheckpointStore
    options:
      show_source: false
      members:
        - save
        - load
        - delete
