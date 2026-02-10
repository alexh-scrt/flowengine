"""Tests for checkpoint/resume system."""

import json

import pytest

from flowengine import (
    BaseComponent,
    FlowConfig,
    FlowContext,
    FlowEngine,
)
from flowengine.core.checkpoint import (
    Checkpoint,
    InMemoryCheckpointStore,
)
from flowengine.config.schema import (
    ComponentConfig,
    FlowDefinition,
    FlowSettings,
    GraphEdgeConfig,
    GraphNodeConfig,
)
from flowengine.errors import FlowExecutionError


# ── Test components ──────────────────────────────────────────────────────────


class AppendComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", [])
        order.append(self.name)
        context.set("order", order)
        return context


class SuspendComponent(BaseComponent):
    """Suspends unless resume_data is present."""

    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", [])
        order.append(self.name)
        context.set("order", order)

        if not context.has("resume_data"):
            context.suspend(self.name, reason="Need approval")
        else:
            resume = context.get("resume_data")
            approved = resume.get("approved", False) if hasattr(resume, "get") else False
            context.set("approval", approved)
        return context


# ── Checkpoint unit tests ────────────────────────────────────────────────────


class TestCheckpointSerialization:
    def test_to_dict_round_trip(self):
        cp = Checkpoint(
            flow_config={"name": "test"},
            context={"data": {"x": 1}},
        )
        d = cp.to_dict()
        restored = Checkpoint.from_dict(d)

        assert restored.checkpoint_id == cp.checkpoint_id
        assert restored.flow_config == cp.flow_config
        assert restored.context == cp.context
        assert restored.created_at == cp.created_at

    def test_to_json_round_trip(self):
        cp = Checkpoint(
            flow_config={"name": "test"},
            context={"data": {"x": 1}},
        )
        j = cp.to_json()
        restored = Checkpoint.from_json(j)

        assert restored.checkpoint_id == cp.checkpoint_id


class TestInMemoryCheckpointStore:
    def test_save_and_load(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(flow_config={}, context={})
        store.save(cp)
        loaded = store.load(cp.checkpoint_id)
        assert loaded is not None
        assert loaded.checkpoint_id == cp.checkpoint_id

    def test_load_missing_returns_none(self):
        store = InMemoryCheckpointStore()
        assert store.load("nonexistent") is None

    def test_delete(self):
        store = InMemoryCheckpointStore()
        cp = Checkpoint(flow_config={}, context={})
        store.save(cp)
        store.delete(cp.checkpoint_id)
        assert store.load(cp.checkpoint_id) is None

    def test_delete_nonexistent_does_not_raise(self):
        store = InMemoryCheckpointStore()
        store.delete("nonexistent")  # Should not raise


class TestContextSuspension:
    def test_suspend_sets_metadata(self):
        context = FlowContext()
        context.suspend("node_1", "Waiting for human")

        assert context.metadata.suspended is True
        assert context.metadata.suspended_at_node == "node_1"
        assert context.metadata.suspension_reason == "Waiting for human"

    def test_suspension_serialization_round_trip(self):
        context = FlowContext()
        context.suspend("node_1", "reason")
        context.metadata.completed_nodes = ["a", "b"]

        d = context.to_dict()
        restored = FlowContext.from_dict(d)

        assert restored.metadata.suspended is True
        assert restored.metadata.suspended_at_node == "node_1"
        assert restored.metadata.suspension_reason == "reason"
        assert restored.metadata.completed_nodes == ["a", "b"]


# ── Engine checkpoint integration tests ──────────────────────────────────────


def _graph_config():
    return FlowConfig(
        name="test-checkpoint",
        version="1.0",
        components=[
            ComponentConfig(name="comp_a", type="t.A"),
            ComponentConfig(name="comp_suspend", type="t.S"),
            ComponentConfig(name="comp_c", type="t.C"),
        ],
        flow=FlowDefinition(
            type="graph",
            settings=FlowSettings(timeout_seconds=60),
            nodes=[
                GraphNodeConfig(id="a", component="comp_a"),
                GraphNodeConfig(id="s", component="comp_suspend"),
                GraphNodeConfig(id="c", component="comp_c"),
            ],
            edges=[
                GraphEdgeConfig(source="a", target="s"),
                GraphEdgeConfig(source="s", target="c"),
            ],
        ),
    )


class TestEngineCheckpoint:
    def test_creates_checkpoint_on_suspension(self):
        store = InMemoryCheckpointStore()
        config = _graph_config()
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_suspend": SuspendComponent("comp_suspend"),
            "comp_c": AppendComponent("comp_c"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, checkpoint_store=store
        )
        result = engine.execute()

        assert result.metadata.suspended is True
        checkpoint_id = result.get("checkpoint_id")
        assert checkpoint_id is not None
        assert store.load(checkpoint_id) is not None

    def test_resume_completes_flow(self):
        store = InMemoryCheckpointStore()
        config = _graph_config()
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_suspend": SuspendComponent("comp_suspend"),
            "comp_c": AppendComponent("comp_c"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, checkpoint_store=store
        )

        # First execution: suspends
        result = engine.execute()
        checkpoint_id = result.get("checkpoint_id")

        # Resume with approval data
        resumed = engine.resume(checkpoint_id, resume_data={"approved": True})

        assert resumed.metadata.suspended is False
        assert resumed.get("approval") is True
        # comp_c should have run
        assert "comp_c" in resumed.get("order")

    def test_resume_deletes_checkpoint(self):
        store = InMemoryCheckpointStore()
        config = _graph_config()
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_suspend": SuspendComponent("comp_suspend"),
            "comp_c": AppendComponent("comp_c"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, checkpoint_store=store
        )

        result = engine.execute()
        checkpoint_id = result.get("checkpoint_id")
        engine.resume(checkpoint_id, resume_data={"approved": True})

        # Checkpoint should be deleted after resume
        assert store.load(checkpoint_id) is None

    def test_resume_invalid_checkpoint_raises(self):
        store = InMemoryCheckpointStore()
        config = _graph_config()
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_suspend": SuspendComponent("comp_suspend"),
            "comp_c": AppendComponent("comp_c"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, checkpoint_store=store
        )
        with pytest.raises(FlowExecutionError, match="Checkpoint not found"):
            engine.resume("nonexistent-id")

    def test_resume_without_store_raises(self):
        config = _graph_config()
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_suspend": SuspendComponent("comp_suspend"),
            "comp_c": AppendComponent("comp_c"),
        }
        engine = FlowEngine(config, instances, validate_types=False)
        with pytest.raises(FlowExecutionError, match="No checkpoint store"):
            engine.resume("some-id")
