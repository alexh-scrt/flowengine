"""FlowEngine checkpoint module.

Provides serializable execution checkpoints for pause/resume support.
"""

from __future__ import annotations

import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Checkpoint:
    """Serializable snapshot of a suspended flow execution."""

    flow_config: dict[str, Any]
    context: dict[str, Any]
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    checkpoint_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "flow_config": self.flow_config,
            "context": self.context,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Checkpoint:
        return cls(
            checkpoint_id=data["checkpoint_id"],
            flow_config=data["flow_config"],
            context=data["context"],
            created_at=data["created_at"],
        )

    @classmethod
    def from_json(cls, json_str: str) -> Checkpoint:
        return cls.from_dict(json.loads(json_str))


class CheckpointStore(ABC):
    """Abstract checkpoint persistence."""

    @abstractmethod
    def save(self, checkpoint: Checkpoint) -> str:
        """Save a checkpoint. Returns checkpoint_id."""
        ...

    @abstractmethod
    def load(self, checkpoint_id: str) -> Checkpoint | None:
        """Load a checkpoint by ID. Returns None if not found."""
        ...

    @abstractmethod
    def delete(self, checkpoint_id: str) -> None:
        """Delete a checkpoint by ID."""
        ...


class InMemoryCheckpointStore(CheckpointStore):
    """Default in-memory store for testing. Production uses DB-backed store."""

    def __init__(self) -> None:
        self._store: dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> str:
        self._store[checkpoint.checkpoint_id] = checkpoint
        return checkpoint.checkpoint_id

    def load(self, checkpoint_id: str) -> Checkpoint | None:
        return self._store.get(checkpoint_id)

    def delete(self, checkpoint_id: str) -> None:
        self._store.pop(checkpoint_id, None)
