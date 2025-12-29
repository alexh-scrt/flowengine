#!/usr/bin/env python3
"""Simple FlowEngine example.

This example demonstrates the basic usage of FlowEngine:
1. Define custom components
2. Load a YAML configuration
3. Execute the flow
4. Access results from context

Run this example:
    python examples/simple_flow.py
"""

from pathlib import Path

from flowengine import BaseComponent, ConfigLoader, FlowContext, FlowEngine


# Define custom components
class GreetComponent(BaseComponent):
    """Component that generates a greeting message."""

    def init(self, config: dict) -> None:
        super().init(config)
        self.greeting = config.get("greeting", "Hello")

    def process(self, context: FlowContext) -> FlowContext:
        name = context.get("name", "World")
        message = f"{self.greeting}, {name}!"
        context.set("message", message)
        print(f"  [GreetComponent] Generated: {message}")
        return context


class ShoutComponent(BaseComponent):
    """Component that converts message to uppercase."""

    def process(self, context: FlowContext) -> FlowContext:
        message = context.get("message", "")
        shouted = message.upper()
        context.set("shouted", shouted)
        print(f"  [ShoutComponent] Converted to: {shouted}")
        return context


def main() -> None:
    """Run the simple flow example."""
    print("=" * 50)
    print("FlowEngine Simple Flow Example")
    print("=" * 50)

    # Load configuration from YAML
    config_path = Path(__file__).parent / "flows" / "simple.yaml"
    config = ConfigLoader.load(config_path)

    print(f"\nLoaded flow: {config.name}")
    print(f"Description: {config.description}")
    print(f"Steps: {[step.component for step in config.steps]}")

    # Create component instances
    components = {
        "greeter": GreetComponent("greeter"),
        "shouter": ShoutComponent("shouter"),
    }

    # Create engine
    engine = FlowEngine(config, components)

    # Validate the flow
    errors = engine.validate()
    if errors:
        print(f"\nValidation errors: {errors}")
        return

    # Execute the flow
    print("\n--- Executing Flow ---")
    context = FlowContext()
    context.set("name", "FlowEngine")

    result = engine.execute(context)

    # Show results
    print("\n--- Results ---")
    print(f"Message: {result.data.message}")
    print(f"Shouted: {result.data.shouted}")
    print(f"\nExecution time: {result.metadata.total_duration:.4f}s")
    print(f"Component timings: {result.metadata.component_timings}")

    print("\n" + "=" * 50)
    print("Flow completed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
