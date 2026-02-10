"""Tests for execution lifecycle hooks."""

import pytest

from flowengine import (
    BaseComponent,
    FlowConfig,
    FlowContext,
    FlowEngine,
)
from flowengine.config.schema import (
    ComponentConfig,
    FlowDefinition,
    FlowSettings,
    GraphEdgeConfig,
    GraphNodeConfig,
)


# ── Test components ──────────────────────────────────────────────────────────


class AppendComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", [])
        order.append(self.name)
        context.set("order", order)
        return context


class FailComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        raise RuntimeError("Intentional failure")


class ConditionComponent(BaseComponent):
    def process(self, context: FlowContext) -> FlowContext:
        self.set_output_port(context, self.config.get("port", "true"))
        return context


# ── Test hook ────────────────────────────────────────────────────────────────


class RecordingHook:
    """Records all hook calls for assertions."""

    def __init__(self):
        self.events: list[tuple[str, tuple]] = []

    def on_node_start(self, node_id, component_name, context):
        self.events.append(("start", (node_id, component_name)))

    def on_node_complete(self, node_id, component_name, context, duration):
        self.events.append(("complete", (node_id, component_name, duration)))

    def on_node_error(self, node_id, component_name, error, context):
        self.events.append(("error", (node_id, component_name, str(error))))

    def on_node_skipped(self, node_id, component_name, reason):
        self.events.append(("skipped", (node_id, component_name, reason)))

    def on_flow_suspended(self, node_id, reason, checkpoint_id):
        self.events.append(("suspended", (node_id, reason)))


class BrokenHook:
    """Hook that raises on every call."""

    def on_node_start(self, node_id, component_name, context):
        raise RuntimeError("Hook failure")

    def on_node_complete(self, node_id, component_name, context, duration):
        raise RuntimeError("Hook failure")

    def on_node_error(self, node_id, component_name, error, context):
        raise RuntimeError("Hook failure")

    def on_node_skipped(self, node_id, component_name, reason):
        raise RuntimeError("Hook failure")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_graph_config(nodes, edges, components, settings=None):
    return FlowConfig(
        name="hook-test",
        version="1.0",
        components=[ComponentConfig(**c) for c in components],
        flow=FlowDefinition(
            type="graph",
            settings=FlowSettings(**(settings or {"timeout_seconds": 60})),
            nodes=[GraphNodeConfig(**n) for n in nodes],
            edges=[GraphEdgeConfig(**e) for e in edges],
        ),
    )


# ── Tests ────────────────────────────────────────────────────────────────────


class TestHookOnNodeStart:
    def test_fires_before_execution(self):
        hook = RecordingHook()
        config = _make_graph_config(
            nodes=[{"id": "a", "component": "comp_a"}],
            edges=[],
            components=[{"name": "comp_a", "type": "t.A"}],
        )
        instances = {"comp_a": AppendComponent("comp_a")}
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[hook]
        )
        engine.execute()

        start_events = [e for e in hook.events if e[0] == "start"]
        assert len(start_events) == 1
        assert start_events[0][1] == ("a", "comp_a")


class TestHookOnNodeComplete:
    def test_fires_with_duration(self):
        hook = RecordingHook()
        config = _make_graph_config(
            nodes=[{"id": "a", "component": "comp_a"}],
            edges=[],
            components=[{"name": "comp_a", "type": "t.A"}],
        )
        instances = {"comp_a": AppendComponent("comp_a")}
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[hook]
        )
        engine.execute()

        complete_events = [e for e in hook.events if e[0] == "complete"]
        assert len(complete_events) == 1
        node_id, comp_name, duration = complete_events[0][1]
        assert node_id == "a"
        assert comp_name == "comp_a"
        assert isinstance(duration, float)
        assert duration >= 0


class TestHookOnNodeError:
    def test_fires_on_failure(self):
        hook = RecordingHook()
        config = _make_graph_config(
            nodes=[{"id": "a", "component": "comp_fail"}],
            edges=[],
            components=[{"name": "comp_fail", "type": "t.F"}],
            settings={"fail_fast": True, "timeout_seconds": 60},
        )
        instances = {"comp_fail": FailComponent("comp_fail")}
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[hook]
        )

        with pytest.raises(Exception):
            engine.execute()

        error_events = [e for e in hook.events if e[0] == "error"]
        assert len(error_events) == 1
        assert error_events[0][1][0] == "a"  # node_id
        assert "Intentional failure" in error_events[0][1][2]


class TestHookOnNodeSkipped:
    def test_fires_for_unreachable(self):
        hook = RecordingHook()
        config = _make_graph_config(
            nodes=[
                {"id": "cond", "component": "comp_cond"},
                {"id": "on_true", "component": "comp_true"},
                {"id": "on_false", "component": "comp_false"},
            ],
            edges=[
                {"source": "cond", "target": "on_true", "port": "true"},
                {"source": "cond", "target": "on_false", "port": "false"},
            ],
            components=[
                {"name": "comp_cond", "type": "t.C", "config": {"port": "true"}},
                {"name": "comp_true", "type": "t.T"},
                {"name": "comp_false", "type": "t.F"},
            ],
        )
        instances = {
            "comp_cond": ConditionComponent("comp_cond"),
            "comp_true": AppendComponent("comp_true"),
            "comp_false": AppendComponent("comp_false"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[hook]
        )
        engine.execute()

        skipped_events = [e for e in hook.events if e[0] == "skipped"]
        assert len(skipped_events) == 1
        assert skipped_events[0][1][0] == "on_false"


class TestHookExceptionDoesNotBreakFlow:
    def test_broken_hook_does_not_break_execution(self):
        broken = BrokenHook()
        recorder = RecordingHook()
        config = _make_graph_config(
            nodes=[
                {"id": "a", "component": "comp_a"},
                {"id": "b", "component": "comp_b"},
            ],
            edges=[{"source": "a", "target": "b"}],
            components=[
                {"name": "comp_a", "type": "t.A"},
                {"name": "comp_b", "type": "t.B"},
            ],
        )
        instances = {
            "comp_a": AppendComponent("comp_a"),
            "comp_b": AppendComponent("comp_b"),
        }
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[broken, recorder]
        )
        result = engine.execute()

        # Flow completes successfully despite broken hook
        assert result.get("order") == ["comp_a", "comp_b"]
        # Recording hook still received events
        assert len(recorder.events) > 0


class TestMultipleHooks:
    def test_all_hooks_receive_events(self):
        hook1 = RecordingHook()
        hook2 = RecordingHook()
        config = _make_graph_config(
            nodes=[{"id": "a", "component": "comp_a"}],
            edges=[],
            components=[{"name": "comp_a", "type": "t.A"}],
        )
        instances = {"comp_a": AppendComponent("comp_a")}
        engine = FlowEngine(
            config, instances, validate_types=False, hooks=[hook1, hook2]
        )
        engine.execute()

        assert len(hook1.events) == len(hook2.events)
        assert hook1.events[0][0] == "start"
        assert hook2.events[0][0] == "start"
