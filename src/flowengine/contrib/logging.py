"""Logging component for FlowEngine.

Provides a component that logs context data at configurable levels.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Literal

from flowengine.core.component import BaseComponent

if TYPE_CHECKING:
    from flowengine.core.context import FlowContext


class LoggingComponent(BaseComponent):
    """Component that logs context data.

    Useful for debugging flows by logging context state at
    specific points in the execution.

    Config:
        level: Log level (debug, info, warning, error). Default: info
        message: Log message template. Default: "Context state"
        log_data: Whether to log context data. Default: True
        log_metadata: Whether to log execution metadata. Default: False
        keys: Specific keys to log (if None, logs all). Default: None

    Example YAML:
        ```yaml
        - name: logger
          type: flowengine.contrib.logging.LoggingComponent
          config:
            level: debug
            message: "After processing"
            log_data: true
            keys:
              - user
              - result
        ```

    Example usage:
        ```python
        logger = LoggingComponent("debug_log")
        logger.init({
            "level": "debug",
            "message": "Current state",
            "keys": ["user", "data"]
        })
        ```
    """

    VALID_LEVELS: tuple[str, ...] = ("debug", "info", "warning", "error")

    def init(self, config: dict[str, Any]) -> None:
        """Initialize with logging configuration.

        Args:
            config: Configuration dictionary
        """
        super().init(config)
        self.level: str = config.get("level", "info")
        self.message: str = config.get("message", "Context state")
        self.log_data: bool = config.get("log_data", True)
        self.log_metadata: bool = config.get("log_metadata", False)
        self.keys: list[str] | None = config.get("keys")

        self._logger = logging.getLogger(f"flowengine.component.{self.name}")

    def validate_config(self) -> list[str]:
        """Validate logging configuration.

        Returns:
            List of validation errors
        """
        errors = super().validate_config()

        if self.level not in self.VALID_LEVELS:
            errors.append(
                f"Invalid log level: {self.level}. "
                f"Must be one of: {self.VALID_LEVELS}"
            )

        return errors

    def process(self, context: FlowContext) -> FlowContext:
        """Log context data.

        Args:
            context: Current flow context

        Returns:
            Unchanged flow context
        """
        log_func = getattr(self._logger, self.level)

        parts: list[str] = [self.message]

        if self.log_data:
            if self.keys:
                # Log specific keys only
                data = {k: context.get(k) for k in self.keys}
            else:
                # Log all data
                data = context.data.to_dict()
            parts.append(f"Data: {data}")

        if self.log_metadata:
            meta = {
                "flow_id": context.metadata.flow_id,
                "timings": context.metadata.component_timings,
                "skipped": context.metadata.skipped_components,
                "errors": len(context.metadata.errors),
            }
            parts.append(f"Metadata: {meta}")

        log_func(" | ".join(parts))

        return context
