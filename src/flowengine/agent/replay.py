"""Deterministic replay — debug and improve generated workers without guessing.

A :class:`RunRecord` durably captures everything needed to reproduce a run: the
normalized flow, the initial inputs, the resulting trace, and the outputs.
:func:`replay` reconstructs the flow from a record and re-executes it — optionally
from a chosen node — so an agent can iterate on a worker against a fixed input.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field

from flowengine.config.schema import FlowConfig
from flowengine.core.context import FlowContext


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRecord(BaseModel):
    """A durable, replayable record of a single flow execution."""

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = Field(default_factory=_now_iso)
    flow_config: dict[str, Any] = Field(..., description="Serialized FlowConfig")
    normalized_yaml: Optional[str] = None
    input_data: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    trace: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_run(
        cls,
        config: FlowConfig,
        input_data: dict[str, Any],
        result: FlowContext,
        created_at: Optional[str] = None,
    ) -> "RunRecord":
        """Capture a record from a completed run.

        Args:
            config: The flow that was executed.
            input_data: The initial context data the flow was given.
            result: The context returned by ``FlowEngine.execute()``.
            created_at: Optional ISO timestamp (defaults to now).
        """
        from flowengine.agent.normalize import normalize_config
        from flowengine.agent.trace import AgentTrace

        trace = AgentTrace.from_context(result, config)
        record = cls(
            run_id=result.metadata.flow_id,
            flow_config=config.model_dump(mode="json"),
            normalized_yaml=normalize_config(config),
            input_data=dict(input_data),
            outputs=trace.outputs,
            trace=trace.to_dict(),
        )
        if created_at is not None:
            record.created_at = created_at
        return record

    def to_config(self) -> FlowConfig:
        """Reconstruct the :class:`FlowConfig` from this record."""
        return FlowConfig.model_validate(self.flow_config)


class RunStore(ABC):
    """Abstract durable store for :class:`RunRecord` objects."""

    @abstractmethod
    def save(self, record: RunRecord) -> str: ...

    @abstractmethod
    def load(self, run_id: str) -> Optional[RunRecord]: ...

    @abstractmethod
    def list_runs(self) -> list[str]: ...

    @abstractmethod
    def delete(self, run_id: str) -> None: ...


class InMemoryRunStore(RunStore):
    """A simple in-memory run store (default; useful for tests and sessions)."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def save(self, record: RunRecord) -> str:
        self._runs[record.run_id] = record
        return record.run_id

    def load(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    def list_runs(self) -> list[str]:
        return list(self._runs.keys())

    def delete(self, run_id: str) -> None:
        self._runs.pop(run_id, None)


def replay(
    run_id: str,
    store: RunStore,
    from_node: Optional[str] = None,
    registry: Any = None,
) -> FlowContext:
    """Re-execute a stored run, optionally resuming from a given node.

    Args:
        run_id: The id of the record to replay.
        store: The store holding the record.
        from_node: For graph flows, mark all nodes before this one (in execution
            order) as already completed, so execution resumes from ``from_node``.
        registry: Optional component registry for instantiation.

    Returns:
        The resulting :class:`FlowContext`.

    Raises:
        KeyError: If ``run_id`` is not found in the store.
    """
    from flowengine.core.engine import FlowEngine

    record = store.load(run_id)
    if record is None:
        raise KeyError(f"No run record found for id: {run_id}")

    config = record.to_config()
    context = FlowContext()
    for key, value in record.input_data.items():
        context.set(key, value)

    if from_node is not None and config.flow.type == "graph":
        from flowengine.agent.plan import explain

        order = explain(config, registry=registry).execution_order
        if from_node in order:
            before = order[: order.index(from_node)]
            context.metadata.completed_nodes = list(before)

    engine = FlowEngine.from_config(config, registry=registry)
    return engine.execute(context)
