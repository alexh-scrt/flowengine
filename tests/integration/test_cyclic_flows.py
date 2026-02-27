"""Integration tests for cyclic graph flows.

Tests YAML-driven agent loops end-to-end:
- YAML parsing → FlowConfig with cyclic graph settings
- Component registration + FlowEngine.from_config()
- Port-based routing through cycles
- Iteration metadata and visit counts
- Checkpoint/resume in cyclic flows
"""

import pytest

from flowengine import (
    BaseComponent,
    ConfigLoader,
    FlowContext,
    FlowEngine,
)
from flowengine.config.registry import ComponentRegistry
from flowengine.errors import MaxIterationsError

# ── Test Components (simulate research agent) ───────────────────────────────


class PlannerComponent(BaseComponent):
    """Plans the next research action. Increments step counter."""

    def process(self, context: FlowContext) -> FlowContext:
        steps = context.get("steps", 0) + 1
        context.set("steps", steps)
        context.set("current_plan", f"Research plan v{steps}")
        log = context.get("log", [])
        log.append(f"plan:{steps}")
        context.set("log", log)
        return context


class SearchComponent(BaseComponent):
    """Simulates searching. Accumulates findings."""

    def process(self, context: FlowContext) -> FlowContext:
        findings = context.get("findings", [])
        step = context.get("steps", 0)
        findings.append(f"finding-{step}")
        context.set("findings", findings)
        log = context.get("log", [])
        log.append(f"search:{step}")
        context.set("log", log)
        return context


class SynthesizeComponent(BaseComponent):
    """Synthesizes findings into a summary."""

    def process(self, context: FlowContext) -> FlowContext:
        findings = context.get("findings", [])
        context.set("summary", f"Synthesis of {len(findings)} findings")
        log = context.get("log", [])
        log.append(f"synthesize:{len(findings)}")
        context.set("log", log)
        return context


class EvaluateComponent(BaseComponent):
    """Evaluates quality. Routes to 'refine' or 'done' based on threshold."""

    def process(self, context: FlowContext) -> FlowContext:
        quality_threshold = self.config.get("quality_threshold", 3)
        findings = context.get("findings", [])
        quality = len(findings)
        context.set("quality_score", quality)

        log = context.get("log", [])
        log.append(f"evaluate:{quality}")
        context.set("log", log)

        if quality >= quality_threshold:
            self.set_output_port(context, "done")
        else:
            self.set_output_port(context, "refine")

        return context


class DeliverComponent(BaseComponent):
    """Delivers the final result."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("delivered", True)
        context.set("final_summary", context.get("summary", "No summary"))
        log = context.get("log", [])
        log.append("deliver")
        context.set("log", log)
        return context


# ── YAML Configurations ──────────────────────────────────────────────────────

RESEARCH_AGENT_YAML = """
name: "Research Agent Loop"
version: "1.0"

components:
  - name: planner
    type: test.PlannerComponent
  - name: searcher
    type: test.SearchComponent
  - name: synthesizer
    type: test.SynthesizeComponent
  - name: evaluator
    type: test.EvaluateComponent
    config:
      quality_threshold: 3
  - name: deliverer
    type: test.DeliverComponent

flow:
  type: graph
  settings:
    timeout_seconds: 30
    max_iterations: 10
    on_max_iterations: exit
  nodes:
    - id: plan
      component: planner
    - id: search
      component: searcher
    - id: synthesize
      component: synthesizer
    - id: evaluate
      component: evaluator
    - id: deliver
      component: deliverer
  edges:
    - source: plan
      target: search
    - source: search
      target: synthesize
    - source: synthesize
      target: evaluate
    - source: evaluate
      target: plan
      port: refine
    - source: evaluate
      target: deliver
      port: done
"""

SIMPLE_CYCLE_YAML = """
name: "Simple Counter Loop"
version: "1.0"

components:
  - name: counter
    type: test.PlannerComponent
  - name: checker
    type: test.EvaluateComponent
    config:
      quality_threshold: 5

flow:
  type: graph
  settings:
    timeout_seconds: 30
    max_iterations: 20
    on_max_iterations: fail
  nodes:
    - id: count
      component: counter
      max_visits: 1000
    - id: check
      component: checker
      max_visits: 1000
  edges:
    - source: count
      target: check
    - source: check
      target: count
      port: refine
"""


# ── Helper ───────────────────────────────────────────────────────────────────


def _make_registry():
    """Create a registry with test components."""
    registry = ComponentRegistry()
    registry.register_class("test.PlannerComponent", PlannerComponent)
    registry.register_class("test.SearchComponent", SearchComponent)
    registry.register_class("test.SynthesizeComponent", SynthesizeComponent)
    registry.register_class("test.EvaluateComponent", EvaluateComponent)
    registry.register_class("test.DeliverComponent", DeliverComponent)
    return registry


# ── Integration Tests ────────────────────────────────────────────────────────


class TestResearchAgentLoop:
    """Full YAML-driven research agent: plan → search → synthesize → evaluate → [refine|deliver]."""

    def test_yaml_config_loads_cyclic_graph(self):
        """YAML with cycles parses successfully."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        assert config.name == "Research Agent Loop"
        assert config.flow.type == "graph"
        assert config.flow.settings.max_iterations == 10
        assert config.flow.settings.on_max_iterations == "exit"
        assert len(config.flow.nodes) == 5
        assert len(config.flow.edges) == 5

    def test_from_config_creates_engine(self):
        """FlowEngine.from_config() works with cyclic YAML."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)
        assert engine is not None
        assert engine.flow_type == "graph"

    def test_research_agent_executes_full_loop(self):
        """Research agent loops until quality threshold met, then delivers."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        # Agent should have delivered
        assert result.get("delivered") is True
        assert result.get("final_summary") is not None

        # Should have accumulated enough findings
        findings = result.get("findings")
        assert len(findings) >= 3  # quality_threshold is 3

        # Delivery should be last in log
        log = result.get("log")
        assert log[-1] == "deliver"

    def test_research_agent_iteration_metadata(self):
        """Iteration metadata is correctly tracked."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        # Should have iterated at least once (loops before quality met)
        assert result.metadata.iteration_count >= 1

        # Visit counts should be set for cycle nodes
        vc = result.metadata.node_visit_counts
        for node in ["plan", "search", "synthesize", "evaluate"]:
            assert node in vc
            assert vc[node] >= 1

    def test_research_agent_port_routing(self):
        """Port routing correctly directs to refine or deliver."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        log = result.get("log")
        # Should see multiple plan/search/synthesize/evaluate cycles
        plan_count = sum(1 for entry in log if entry.startswith("plan:"))
        assert plan_count >= 2  # At least 2 planning iterations

        # Final entry is deliver
        assert log[-1] == "deliver"

    def test_research_agent_quality_score(self):
        """Quality score meets threshold when agent exits."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        quality = result.get("quality_score")
        assert quality >= 3  # Threshold is 3

    def test_research_agent_with_initial_data(self):
        """Agent can start with pre-seeded context data."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        ctx = FlowContext()
        ctx.set("findings", ["pre-existing-1", "pre-existing-2"])
        result = engine.execute(ctx)

        # Should deliver quickly (2 pre-existing + 1 new = 3 >= threshold)
        assert result.get("delivered") is True
        findings = result.get("findings")
        assert "pre-existing-1" in findings
        assert "pre-existing-2" in findings

    def test_deliver_node_in_completed_nodes(self):
        """Terminal deliver node tracked in completed_nodes."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        assert "deliver" in result.metadata.completed_nodes

    def test_cycle_nodes_not_in_completed_nodes(self):
        """Cycle-participating nodes are NOT in completed_nodes."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        for node in ["plan", "search", "synthesize", "evaluate"]:
            assert node not in result.metadata.completed_nodes


class TestSimpleCycleYAML:
    """Simple counter cycle loaded from YAML."""

    def test_simple_cycle_max_iterations_fail(self):
        """Counter loop raises MaxIterationsError when threshold can't be met."""
        # The simple cycle uses PlannerComponent (increments 'steps') but
        # EvaluateComponent checks len(findings) which stays at 0.
        # So it always routes to 'refine' and hits max_iterations.
        config = ConfigLoader.loads(SIMPLE_CYCLE_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        with pytest.raises(MaxIterationsError):
            engine.execute()

    def test_yaml_settings_propagate(self):
        """YAML settings for max_iterations and on_max_iterations are honored."""
        config = ConfigLoader.loads(SIMPLE_CYCLE_YAML)
        assert config.flow.settings.max_iterations == 20
        assert config.flow.settings.on_max_iterations == "fail"


class TestCyclicFlowMetadataRoundTrip:
    """Test that cyclic flow metadata survives serialization."""

    def test_context_round_trip_preserves_cyclic_state(self):
        """to_dict/from_dict preserves cyclic execution state."""
        config = ConfigLoader.loads(RESEARCH_AGENT_YAML)
        registry = _make_registry()
        engine = FlowEngine.from_config(config, registry=registry)

        result = engine.execute()

        # Serialize
        data = result.to_dict()

        # Deserialize
        restored = FlowContext.from_dict(data)

        # Verify cyclic state preserved
        assert restored.metadata.node_visit_counts == result.metadata.node_visit_counts
        assert restored.metadata.iteration_count == result.metadata.iteration_count
        assert restored.metadata.max_iterations_reached == result.metadata.max_iterations_reached
        assert restored.get("delivered") is True
        assert restored.get("findings") == result.get("findings")
