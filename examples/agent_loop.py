#!/usr/bin/env python3
"""Agent Loop Example — Cyclic Graph Execution (v0.3.0).

This example demonstrates the core agentic AI pattern using FlowEngine's
cyclic graph execution:

    plan -> execute -> observe -> evaluate -> [refine -> plan | done -> deliver]

The evaluator component checks the quality of accumulated results and
routes back to the planning phase (via the "refine" port) until the
quality threshold is met, then routes to delivery (via the "done" port).

Key v0.3.0 features demonstrated:
- Cyclic graph execution with back-edges
- Port-based routing to exit loops
- Iteration counting and visit tracking
- max_iterations safety limit

Run this example:
    python examples/agent_loop.py
"""

from pathlib import Path

from flowengine import BaseComponent, ConfigLoader, FlowContext, FlowEngine
from flowengine.config.registry import ComponentRegistry

# ── Agent Components ─────────────────────────────────────────────────────────


class PlanComponent(BaseComponent):
    """Plans the next action based on current state."""

    def process(self, context: FlowContext) -> FlowContext:
        iteration = context.get("iteration", 0) + 1
        context.set("iteration", iteration)
        context.set("plan", f"Research plan v{iteration}")
        print(f"  [Plan] Iteration {iteration}: Creating research plan v{iteration}")
        return context


class ExecuteComponent(BaseComponent):
    """Executes the plan and produces results."""

    def process(self, context: FlowContext) -> FlowContext:
        iteration = context.get("iteration", 1)
        results = context.get("results", [])
        new_result = f"finding-{iteration}"
        results.append(new_result)
        context.set("results", results)
        print(f"  [Execute] Found: {new_result} (total: {len(results)})")
        return context


class ObserveComponent(BaseComponent):
    """Observes and summarizes the accumulated results."""

    def process(self, context: FlowContext) -> FlowContext:
        results = context.get("results", [])
        summary = f"Synthesis of {len(results)} findings"
        context.set("summary", summary)
        print(f"  [Observe] {summary}")
        return context


class EvaluateComponent(BaseComponent):
    """Evaluates quality and decides whether to refine or deliver."""

    def process(self, context: FlowContext) -> FlowContext:
        threshold = self.config.get("quality_threshold", 3)
        results = context.get("results", [])
        quality = len(results)
        context.set("quality", quality)

        if quality >= threshold:
            self.set_output_port(context, "done")
            print(f"  [Evaluate] Quality {quality}/{threshold} - DONE! Routing to deliver.")
        else:
            self.set_output_port(context, "refine")
            print(f"  [Evaluate] Quality {quality}/{threshold} - needs more work. Looping back.")

        return context


class DeliverComponent(BaseComponent):
    """Delivers the final result."""

    def process(self, context: FlowContext) -> FlowContext:
        summary = context.get("summary", "No summary")
        results = context.get("results", [])
        context.set("delivered", True)
        context.set("final_output", {
            "summary": summary,
            "result_count": len(results),
            "results": results,
        })
        print(f"  [Deliver] Final delivery: {summary}")
        return context


# ── Main ─────────────────────────────────────────────────────────────────────


def main() -> None:
    """Run the agent loop example."""
    print("=" * 60)
    print("FlowEngine Agent Loop Example (v0.3.0)")
    print("Pattern: plan -> execute -> observe -> evaluate -> [loop|deliver]")
    print("=" * 60)

    # Load YAML configuration
    config_path = Path(__file__).parent / "flows" / "agent_loop.yaml"
    config = ConfigLoader.load(config_path)

    # Register components
    registry = ComponentRegistry()
    registry.register_class("examples.agent_loop.PlanComponent", PlanComponent)
    registry.register_class("examples.agent_loop.ExecuteComponent", ExecuteComponent)
    registry.register_class("examples.agent_loop.ObserveComponent", ObserveComponent)
    registry.register_class("examples.agent_loop.EvaluateComponent", EvaluateComponent)
    registry.register_class("examples.agent_loop.DeliverComponent", DeliverComponent)

    # Create engine from config
    engine = FlowEngine.from_config(config, registry=registry)

    print(f"\nFlow: {config.name}")
    print(f"Max iterations: {config.flow.settings.max_iterations}")
    print(f"On max iterations: {config.flow.settings.on_max_iterations}")
    print()

    # Execute
    result = engine.execute()

    # Show results
    print()
    print("-" * 60)
    print("Results:")
    print(f"  Delivered: {result.get('delivered')}")
    print(f"  Quality: {result.get('quality')}")
    print(f"  Results: {result.get('results')}")
    print(f"  Summary: {result.get('summary')}")

    print()
    print("Execution Metadata:")
    print(f"  Iteration count: {result.metadata.iteration_count}")
    print(f"  Visit counts: {result.metadata.node_visit_counts}")
    print(f"  Max iterations reached: {result.metadata.max_iterations_reached}")
    print(f"  Completed nodes: {result.metadata.completed_nodes}")

    timings = result.metadata.component_timings
    print(f"  Component timings: {', '.join(f'{k}={v:.4f}s' for k, v in timings.items())}")
    print("=" * 60)


if __name__ == "__main__":
    main()
