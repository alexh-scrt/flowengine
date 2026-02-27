"""FlowEngine exception hierarchy.

This module defines the custom exception types used throughout FlowEngine.
All exceptions inherit from FlowEngineError for easy catching.
"""

from typing import Optional


class FlowEngineError(Exception):
    """Base exception for all FlowEngine errors."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ConfigurationError(FlowEngineError):
    """Error in flow configuration.

    Raised when there are issues with YAML parsing, schema validation,
    or invalid configuration values.

    Attributes:
        config_path: Path to the configuration file (if applicable)
        details: List of specific validation errors
    """

    def __init__(
        self,
        message: str,
        config_path: Optional[str] = None,
        details: Optional[list[str]] = None,
    ) -> None:
        self.config_path = config_path
        self.details = details or []

        full_message = message
        if config_path:
            full_message = f"{config_path}: {message}"
        if details:
            full_message += f"\nDetails: {details}"

        super().__init__(full_message)


class FlowExecutionError(FlowEngineError):
    """Error during flow execution.

    Raised when the flow execution fails for reasons other than
    component-specific errors.

    Attributes:
        flow_id: Unique identifier of the flow execution
        step: Name of the step where error occurred
    """

    def __init__(
        self,
        message: str,
        flow_id: Optional[str] = None,
        step: Optional[str] = None,
    ) -> None:
        self.flow_id = flow_id
        self.step = step

        full_message = message
        if flow_id:
            full_message = f"[{flow_id}] {message}"
        if step:
            full_message = f"{full_message} (step: {step})"

        super().__init__(full_message)


class ComponentError(FlowEngineError):
    """Error from a component.

    Raised when a component fails during its lifecycle methods.

    Attributes:
        component: Name of the component that failed
        original_error: The underlying exception (if any)
    """

    def __init__(
        self,
        component: str,
        message: str,
        original_error: Optional[Exception] = None,
    ) -> None:
        self.component = component
        self.original_error = original_error

        full_message = f"Component '{component}' failed: {message}"
        super().__init__(full_message)


class ConditionEvaluationError(FlowEngineError):
    """Error evaluating a condition expression.

    Raised when a condition expression is invalid, unsafe,
    or fails during evaluation.

    Attributes:
        condition: The condition expression string
    """

    def __init__(
        self,
        message: str,
        condition: Optional[str] = None,
    ) -> None:
        self.condition = condition

        full_message = message
        if condition:
            full_message = f"{message}\nCondition: {condition}"

        super().__init__(full_message)


class FlowTimeoutError(FlowExecutionError):
    """Error when flow execution exceeds timeout.

    Raised when the total flow execution time exceeds the configured
    timeout_seconds value, or when a component's check_deadline() call
    detects the deadline has passed.

    Attributes:
        timeout: The configured timeout in seconds (None if from deadline check)
        elapsed: How much time had elapsed when timeout occurred
    """

    def __init__(
        self,
        message: str,
        timeout: Optional[float],
        elapsed: float,
        flow_id: Optional[str] = None,
        step: Optional[str] = None,
    ) -> None:
        self.timeout = timeout
        self.elapsed = elapsed
        super().__init__(message, flow_id=flow_id, step=step)


class MaxIterationsError(FlowExecutionError):
    """Raised when a cyclic graph exceeds max_iterations.

    Attributes:
        max_iterations: The configured iteration limit
        actual_iterations: How many iterations were attempted
        cycle_entry_node: The node ID where the cycle re-enters
    """

    def __init__(
        self,
        message: str,
        *,
        max_iterations: int,
        actual_iterations: int,
        cycle_entry_node: str,
        flow_id: Optional[str] = None,
    ) -> None:
        self.max_iterations = max_iterations
        self.actual_iterations = actual_iterations
        self.cycle_entry_node = cycle_entry_node
        super().__init__(message, flow_id=flow_id, step=cycle_entry_node)


class DeadlineCheckError(FlowExecutionError):
    """Error when component fails to check deadline.

    Raised when require_deadline_check is True and a long-running component
    does not call check_deadline() during execution. This enforces the
    cooperative timeout contract.

    Attributes:
        component: Name of the non-compliant component
        duration: How long the component took to execute
        threshold: The threshold above which deadline checks are required
    """

    def __init__(
        self,
        message: str,
        component: str,
        duration: float,
        threshold: float,
        flow_id: Optional[str] = None,
    ) -> None:
        self.component = component
        self.duration = duration
        self.threshold = threshold
        super().__init__(message, flow_id=flow_id, step=component)
