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
        - teardown
        - validate_config
        - health_check
        - check_deadline
        - name
        - config
        - is_initialized

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
