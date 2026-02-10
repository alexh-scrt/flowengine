"""Tests for async component support."""

import asyncio

import pytest

from flowengine import BaseComponent, FlowContext


# ── Test components ──────────────────────────────────────────────────────────


class SyncComponent(BaseComponent):
    """Standard sync component."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("sync_ran", True)
        return context


class AsyncComponent(BaseComponent):
    """Component with native async processing."""

    def process(self, context: FlowContext) -> FlowContext:
        # Sync fallback (should not be used when async path available)
        context.set("sync_fallback", True)
        return context

    async def process_async(self, context: FlowContext) -> FlowContext:
        # Simulate async work
        await asyncio.sleep(0.01)
        context.set("async_ran", True)
        return context


class AsyncErrorComponent(BaseComponent):
    """Async component that raises."""

    def process(self, context: FlowContext) -> FlowContext:
        return context

    async def process_async(self, context: FlowContext) -> FlowContext:
        raise ValueError("Async failure")


# ── Tests ────────────────────────────────────────────────────────────────────


class TestIsAsyncProperty:
    def test_sync_component_is_not_async(self):
        comp = SyncComponent("sync")
        assert comp.is_async is False

    def test_async_component_is_async(self):
        comp = AsyncComponent("async")
        assert comp.is_async is True

    def test_base_default_is_not_async(self):
        """A component that only implements process() is not async."""
        comp = SyncComponent("test")
        comp.init({})
        assert comp.is_async is False


class TestProcessAsync:
    @pytest.mark.asyncio
    async def test_sync_fallback_via_process_async(self):
        """Default process_async calls sync process()."""
        comp = SyncComponent("sync")
        comp.init({})
        context = FlowContext()
        result = await comp.process_async(context)
        assert result.get("sync_ran") is True

    @pytest.mark.asyncio
    async def test_async_override_runs(self):
        comp = AsyncComponent("async")
        comp.init({})
        context = FlowContext()
        result = await comp.process_async(context)
        assert result.get("async_ran") is True
        assert result.get("sync_fallback") is None

    @pytest.mark.asyncio
    async def test_async_error_propagates(self):
        comp = AsyncErrorComponent("err")
        comp.init({})
        context = FlowContext()
        with pytest.raises(ValueError, match="Async failure"):
            await comp.process_async(context)


class TestSetOutputPort:
    def test_set_output_port(self):
        comp = SyncComponent("test")
        comp.init({})
        context = FlowContext()
        comp.set_output_port(context, "true")
        assert context.get_active_port() == "true"

    def test_port_cleared(self):
        context = FlowContext()
        context.set_port("some_port")
        assert context.get_active_port() == "some_port"
        context.clear_port()
        assert context.get_active_port() is None
