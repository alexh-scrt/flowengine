"""FlowEngine configuration schema models.

This module defines Pydantic models for validating flow configurations.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ComponentConfig(BaseModel):
    """Configuration for a single component.

    Attributes:
        name: Unique component name within the flow
        type: Component class path (e.g., "myapp.components.MyComponent")
        config: Component-specific configuration dictionary
    """

    name: str = Field(..., description="Unique component name")
    type: str = Field(..., description="Component class path")
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific configuration",
    )


class FlowSettings(BaseModel):
    """Flow execution settings.

    Attributes:
        fail_fast: If True, stop on first error. Default True.
        timeout_seconds: Maximum flow execution time. Default 300.
        timeout_mode: How to enforce timeouts:
            - "cooperative": Components must call check_deadline() (default)
            - "hard_async": Use asyncio.wait_for for async component execution
            - "hard_process": Run steps in separate processes with hard kill
        require_deadline_check: If True, raise error when long-running components
            don't call check_deadline() (only applies to cooperative mode).
            Default False (only warns).
        on_condition_error: How to handle condition evaluation errors:
            - "fail": Raise ConditionEvaluationError (default)
            - "skip": Skip the step and record the error
            - "warn": Log a warning and skip the step
    """

    fail_fast: bool = Field(
        default=True,
        description="Stop on first error",
    )
    timeout_seconds: float = Field(
        default=300.0,
        description="Maximum flow execution time",
        gt=0,
    )
    timeout_mode: Literal["cooperative", "hard_async", "hard_process"] = Field(
        default="cooperative",
        description=(
            "Timeout enforcement mode: 'cooperative' (components call check_deadline), "
            "'hard_async' (asyncio.wait_for), 'hard_process' (process isolation)"
        ),
    )
    require_deadline_check: bool = Field(
        default=False,
        description=(
            "If True, raise error when long-running components don't call "
            "check_deadline() in cooperative mode. Default False (only warns)."
        ),
    )
    on_condition_error: Literal["fail", "skip", "warn"] = Field(
        default="fail",
        description="How to handle condition evaluation errors",
    )


class StepConfig(BaseModel):
    """Configuration for a single execution step.

    Attributes:
        component: Name of component to execute
        description: Human-readable step description
        condition: Python expression for conditional execution
        on_error: How to handle errors (fail/skip/continue)
    """

    component: str = Field(..., description="Component name to execute")
    description: Optional[str] = Field(
        default=None,
        description="Human-readable step description",
    )
    condition: Optional[str] = Field(
        default=None,
        description="Python expression for conditional execution",
    )
    on_error: Literal["fail", "skip", "continue"] = Field(
        default="fail",
        description="Error handling behavior",
    )


class FlowDefinition(BaseModel):
    """Flow structure definition.

    Attributes:
        type: Flow execution type that determines how steps are processed:
            - "sequential": (default) Runs all steps in order. Conditions guard
              individual steps - if a step's condition is False, it's skipped
              and the next step runs. All matching steps execute.
            - "conditional": First-match branching (like switch/case). Stops
              after the first step whose condition evaluates to True. Only one
              step executes. Defaults on_condition_error to "skip".
        settings: Execution settings
        steps: Ordered list of execution steps
    """

    type: Literal["sequential", "conditional"] = Field(
        default="sequential",
        description=(
            "Flow execution type: 'sequential' runs all matching steps, "
            "'conditional' stops after first match (switch/case semantics)"
        ),
    )
    settings: FlowSettings = Field(
        default_factory=FlowSettings,
        description="Execution settings",
    )
    steps: list[StepConfig] = Field(
        ...,
        description="Ordered list of execution steps",
        min_length=1,
    )


class FlowConfig(BaseModel):
    """Complete flow configuration.

    This is the root model for a flow configuration file.

    Attributes:
        name: Human-readable flow name
        version: Configuration version string
        description: Optional flow description
        components: List of component definitions
        flow: Flow definition with steps

    Example YAML:
        ```yaml
        name: "My Flow"
        version: "1.0"
        components:
          - name: fetcher
            type: myapp.FetchComponent
            config:
              url: "https://api.example.com"
        flow:
          type: sequential
          steps:
            - component: fetcher
        ```
    """

    name: str = Field(..., description="Flow name")
    version: str = Field(default="1.0", description="Configuration version")
    description: Optional[str] = Field(
        default=None,
        description="Flow description",
    )
    components: list[ComponentConfig] = Field(
        ...,
        description="Component definitions",
        min_length=1,
    )
    flow: FlowDefinition = Field(..., description="Flow definition")

    @field_validator("components")
    @classmethod
    def validate_unique_names(
        cls, v: list[ComponentConfig]
    ) -> list[ComponentConfig]:
        """Ensure all component names are unique."""
        names = [c.name for c in v]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate component names: {set(duplicates)}")
        return v

    @field_validator("flow")
    @classmethod
    def validate_step_components(
        cls, v: FlowDefinition, info: Any
    ) -> FlowDefinition:
        """Ensure all steps reference defined components."""
        # Get component names from the already validated components field
        if "components" in info.data:
            component_names = {c.name for c in info.data["components"]}
            for step in v.steps:
                if step.component not in component_names:
                    raise ValueError(
                        f"Step references undefined component: {step.component}"
                    )
        return v

    @property
    def settings(self) -> FlowSettings:
        """Shortcut to flow settings."""
        return self.flow.settings

    @property
    def steps(self) -> list[StepConfig]:
        """Shortcut to flow steps."""
        return self.flow.steps

    def get_component_config(self, name: str) -> Optional[ComponentConfig]:
        """Get configuration for a named component.

        Args:
            name: Component name to find

        Returns:
            ComponentConfig if found, None otherwise
        """
        for comp in self.components:
            if comp.name == name:
                return comp
        return None
