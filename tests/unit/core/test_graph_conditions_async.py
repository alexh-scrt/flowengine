"""Tests for GraphExecutor edge conditions and async component execution."""

import pytest

from flowengine import BaseComponent, FlowContext
from flowengine.config.schema import (
    FlowSettings,
    GraphEdgeConfig,
    GraphNodeConfig,
)
from flowengine.core.graph import GraphExecutor
from flowengine.errors import ConditionEvaluationError


class Mark(BaseComponent):
    """Append name to order; bump 'score'."""

    def process(self, context: FlowContext) -> FlowContext:
        order = context.get("order", [])
        order.append(self.name)
        context.set("order", order)
        context.set("score", context.get("score", 0) + 1)
        return context


class AsyncMark(BaseComponent):
    """Async twin of Mark (coroutine process)."""

    async def process(self, context: FlowContext) -> FlowContext:
        import asyncio

        await asyncio.sleep(0)
        order = context.get("order", [])
        order.append(self.name)
        context.set("order", order)
        return context


def _exec(nodes, edges, components, settings=None):
    return GraphExecutor(
        nodes=[GraphNodeConfig(**n) for n in nodes],
        edges=[GraphEdgeConfig(**e) for e in edges],
        components=components,
        settings=settings or FlowSettings(),
    )


# ── edge conditions ─────────────────────────────────────────────────────────


def test_edge_condition_routes_only_true_branch():
    ex = _exec(
        nodes=[{"id": "s", "component": "s"},
               {"id": "a", "component": "a"},
               {"id": "b", "component": "b"}],
        edges=[{"source": "s", "target": "a",
                "condition": "context.data.score > 0"},
               {"source": "s", "target": "b",
                "condition": "context.data.score > 5"}],
        components={"s": Mark("s"), "a": Mark("a"), "b": Mark("b")},
    )
    out = ex.execute(FlowContext())
    assert out.get("order") == ["s", "a"]  # b's condition was False


def test_edge_condition_combines_with_port():
    # Edge fires only if port matches AND condition holds.
    class PortMark(BaseComponent):
        def process(self, context: FlowContext) -> FlowContext:
            self.set_output_port(context, "go")
            context.set("score", 10)
            return context

    ex = _exec(
        nodes=[{"id": "s", "component": "s"},
               {"id": "a", "component": "a"},
               {"id": "b", "component": "b"}],
        edges=[{"source": "s", "target": "a", "port": "go",
                "condition": "context.data.score > 5"},
               {"source": "s", "target": "b", "port": "go",
                "condition": "context.data.score > 50"}],
        components={"s": PortMark("s"), "a": Mark("a"), "b": Mark("b")},
    )
    out = ex.execute(FlowContext())
    assert out.get("order") == ["a"]


def test_on_condition_error_fail_raises():
    ex = _exec(
        nodes=[{"id": "s", "component": "s"}, {"id": "a", "component": "a"}],
        edges=[{"source": "s", "target": "a", "condition": "this is not valid"}],
        components={"s": Mark("s"), "a": Mark("a")},
        settings=FlowSettings(on_condition_error="fail"),
    )
    with pytest.raises(ConditionEvaluationError):
        ex.execute(FlowContext())


def test_on_condition_error_skip_deactivates_edge():
    ex = _exec(
        nodes=[{"id": "s", "component": "s"}, {"id": "a", "component": "a"}],
        edges=[{"source": "s", "target": "a", "condition": "this is not valid"}],
        components={"s": Mark("s"), "a": Mark("a")},
        settings=FlowSettings(on_condition_error="skip"),
    )
    out = ex.execute(FlowContext())
    assert out.get("order") == ["s"]  # 'a' not activated
    assert out.metadata.condition_errors  # error recorded


# ── async execution ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_async_with_async_components():
    ex = _exec(
        nodes=[{"id": "s", "component": "s"}, {"id": "a", "component": "a"}],
        edges=[{"source": "s", "target": "a"}],
        components={"s": AsyncMark("s"), "a": AsyncMark("a")},
    )
    out = await ex.execute_async(FlowContext())
    assert out.get("order") == ["s", "a"]


@pytest.mark.asyncio
async def test_execute_async_with_sync_components():
    # Sync components must still work on the async path (no await needed).
    ex = _exec(
        nodes=[{"id": "s", "component": "s"}, {"id": "a", "component": "a"}],
        edges=[{"source": "s", "target": "a"}],
        components={"s": Mark("s"), "a": Mark("a")},
    )
    out = await ex.execute_async(FlowContext())
    assert out.get("order") == ["s", "a"]


@pytest.mark.asyncio
async def test_execute_async_honors_edge_condition():
    ex = _exec(
        nodes=[{"id": "s", "component": "s"},
               {"id": "a", "component": "a"},
               {"id": "b", "component": "b"}],
        edges=[{"source": "s", "target": "a",
                "condition": "context.data.flag == True"},
               {"source": "s", "target": "b",
                "condition": "context.data.flag == False"}],
        components={"s": AsyncMark("s"), "a": AsyncMark("a"),
                    "b": AsyncMark("b")},
    )
    ctx = FlowContext()
    ctx.set("flag", True)
    out = await ex.execute_async(ctx)
    assert "a" in out.get("order") and "b" not in out.get("order")


@pytest.mark.asyncio
async def test_execute_async_cyclic_with_max_iterations():
    # Self-loop bounded by max_iterations; async path.
    class Loop(BaseComponent):
        async def process(self, context: FlowContext) -> FlowContext:
            context.set("n", context.get("n", 0) + 1)
            self.set_output_port(context, "again")
            return context

    ex = _exec(
        nodes=[{"id": "loop", "component": "loop"}],
        edges=[{"source": "loop", "target": "loop", "port": "again"}],
        components={"loop": Loop("loop")},
        settings=FlowSettings(max_iterations=3, on_max_iterations="exit"),
    )
    out = await ex.execute_async(FlowContext())
    assert out.get("n") >= 1
    assert out.metadata.iteration_count <= 4
