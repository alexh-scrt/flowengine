"""Agent-optimized execution trace.

FlowEngine already records rich execution metadata (timings, errors, skips,
iteration counts). :class:`AgentTrace` reshapes that into a stable JSON document
designed for an LLM to interpret after a run: *did it succeed, what did it
produce, what ran, what failed, and is there anything to repair?*
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from flowengine.config.schema import FlowConfig
from flowengine.core.context import FlowContext

RunStatus = Literal["completed", "suspended", "error"]


class StepTrace(BaseModel):
    """One executed (or skipped) step in agent-facing form."""

    component: str
    status: Literal["completed", "skipped"]
    duration_ms: Optional[float] = None
    execution_order: Optional[int] = None
    started_at: Optional[str] = None


class AgentTrace(BaseModel):
    """A structured, LLM-friendly record of a single flow run."""

    run_id: str
    status: RunStatus
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[StepTrace] = Field(default_factory=list)
    errors: list[dict[str, Any]] = Field(default_factory=list)
    iterations: int = 0
    max_iterations_reached: bool = False
    suspended_at: Optional[str] = None
    suspension_reason: Optional[str] = None
    total_duration_ms: Optional[float] = None
    repair_hints: list[dict[str, Any]] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)

    @classmethod
    def from_context(
        cls,
        context: FlowContext,
        config: Optional[FlowConfig] = None,
    ) -> "AgentTrace":
        """Build an :class:`AgentTrace` from a finished flow's context.

        Args:
            context: The context returned by ``FlowEngine.execute()``.
            config: Optional flow config; when it declares ``outputs``, the
                trace narrows ``outputs`` to just the declared contract keys.
        """
        meta = context.metadata

        if meta.suspended:
            status: RunStatus = "suspended"
        elif meta.has_errors:
            status = "error"
        else:
            status = "completed"

        steps: list[StepTrace] = [
            StepTrace(
                component=t.component,
                status="completed",
                duration_ms=round(t.duration * 1000, 3),
                execution_order=t.execution_order,
                started_at=t.started_at.isoformat() if t.started_at else None,
            )
            for t in meta.step_timings
        ]
        for skipped in meta.skipped_components:
            steps.append(StepTrace(component=skipped, status="skipped"))

        data = context.data.to_dict()
        if config is not None and config.outputs:
            outputs = {k: data.get(k) for k in config.outputs}
        else:
            outputs = data

        total_ms = (
            round(meta.total_duration * 1000, 3)
            if meta.total_duration is not None
            else None
        )

        return cls(
            run_id=meta.flow_id,
            status=status,
            outputs=outputs,
            steps=steps,
            errors=list(meta.errors),
            iterations=meta.iteration_count,
            max_iterations_reached=meta.max_iterations_reached,
            suspended_at=meta.suspended_at_node,
            suspension_reason=meta.suspension_reason,
            total_duration_ms=total_ms,
        )
