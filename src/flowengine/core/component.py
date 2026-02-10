"""FlowEngine component module.

This module provides the BaseComponent abstract base class that
all flow components must inherit from.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from flowengine.core.context import FlowContext


class BaseComponent(ABC):
    """Abstract base class for all flow components.

    Components are the building blocks of flows. Each component:
    - Has a unique name within the flow
    - Receives configuration at initialization
    - Processes context and returns updated context

    Lifecycle:
        1. __init__(name) - Instance creation
        2. init(config) - Configuration initialization (once)
        3. setup(context) - Pre-processing (each run)
        4. process(context) - Main logic (each run)
        5. teardown(context) - Post-processing (each run)

    Example:
        ```python
        class GreetingComponent(BaseComponent):
            def init(self, config: dict) -> None:
                super().init(config)
                self.greeting = config.get("greeting", "Hello")

            def process(self, context: FlowContext) -> FlowContext:
                name = context.get("name", "World")
                context.set("message", f"{self.greeting}, {name}!")
                return context
        ```
    """

    def __init__(self, name: str) -> None:
        """Initialize component with a name.

        Args:
            name: Unique identifier for this component instance
        """
        self._name = name
        self._config: dict[str, Any] = {}
        self._initialized: bool = False

    @property
    def name(self) -> str:
        """Component's unique name."""
        return self._name

    @property
    def config(self) -> dict[str, Any]:
        """Component's configuration dictionary."""
        return self._config

    @property
    def is_initialized(self) -> bool:
        """Whether init() has been called."""
        return self._initialized

    def init(self, config: dict[str, Any]) -> None:
        """Initialize component with configuration.

        Called once when the flow is set up. Override to perform
        one-time setup like creating clients or loading resources.

        Args:
            config: Configuration dictionary from YAML
        """
        self._config = config
        self._initialized = True

    def setup(self, context: FlowContext) -> None:
        """Prepare for processing.

        Called at the start of each flow execution, before process().
        Override to perform per-run setup.

        Args:
            context: The current flow context
        """
        pass

    @abstractmethod
    def process(self, context: FlowContext) -> FlowContext:
        """Execute component logic.

        The main processing method. Must be implemented by subclasses.

        Args:
            context: Current flow context with accumulated data

        Returns:
            Updated flow context (may be the same instance)
        """
        pass

    def teardown(self, context: FlowContext) -> None:
        """Cleanup after processing.

        Called after process() completes, even if it raised an exception.
        Override to perform cleanup like closing connections.

        Args:
            context: The current flow context
        """
        pass

    def validate_config(self) -> list[str]:
        """Validate component configuration.

        Override to add custom validation logic.

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    async def process_async(self, context: FlowContext) -> FlowContext:
        """Async processing. Override for native async operations.

        Default implementation calls sync process() — no breaking change.
        """
        return self.process(context)

    @property
    def is_async(self) -> bool:
        """True if this component overrides process_async with custom logic."""
        return type(self).process_async is not BaseComponent.process_async

    def set_output_port(self, context: FlowContext, port: str) -> None:
        """Signal which output port to activate.

        Use in components with multiple outputs (e.g., Condition, Switch).
        The graph executor will route to edges matching this port.
        """
        context.set_port(port)

    def health_check(self) -> bool:
        """Check if component is healthy.

        Override to add custom health checking.

        Returns:
            True if component is operational
        """
        return self._initialized

    def check_deadline(self, context: FlowContext) -> None:
        """Check if the execution deadline has been exceeded.

        Call this periodically in long-running process() methods to
        cooperatively support timeout enforcement. If the deadline
        has passed, raises FlowTimeoutError.

        Args:
            context: The current flow context

        Raises:
            FlowTimeoutError: If the deadline has been exceeded

        Example:
            ```python
            def process(self, context: FlowContext) -> FlowContext:
                for item in large_dataset:
                    self.check_deadline(context)  # Check periodically
                    process_item(item)
                return context
            ```
        """
        from flowengine.errors import FlowTimeoutError

        # Mark that deadline was checked (for detection/warning purposes)
        context.metadata.deadline_checked = True

        deadline = context.metadata.deadline
        if deadline is not None and time.time() > deadline:
            elapsed = time.time() - deadline
            raise FlowTimeoutError(
                f"Deadline exceeded by {elapsed:.2f}s in component '{self._name}'",
                timeout=None,
                elapsed=elapsed,
                flow_id=context.metadata.flow_id,
                step=self._name,
            )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self._name!r})"
