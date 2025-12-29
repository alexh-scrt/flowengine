#!/usr/bin/env python3
"""Sequential flow with conditional steps example.

This example demonstrates sequential flow with conditional step execution:
1. Flow type is "sequential" - all steps are evaluated in order
2. Each step can have a condition that guards whether IT runs
3. Conditions are evaluated safely using Python expressions
4. Skipped steps are tracked in metadata

Note: For first-match branching (switch/case semantics), use flow.type: "conditional"

Run this example:
    python examples/conditional_flow.py
"""

from pathlib import Path

from flowengine import BaseComponent, ConfigLoader, FlowContext, FlowEngine


# Define components
class FetchDataComponent(BaseComponent):
    """Simulates fetching data from an API."""

    def process(self, context: FlowContext) -> FlowContext:
        # Simulate API response
        simulate_error = context.get("simulate_error", False)

        if simulate_error:
            context.set("fetch_result", {
                "status": "error",
                "data": None,
                "error": "Simulated API error",
            })
            print("  [FetchData] API returned error")
        else:
            context.set("fetch_result", {
                "status": "success",
                "data": {"users": ["Alice", "Bob", "Charlie"]},
            })
            print("  [FetchData] Fetched 3 users successfully")

        return context


class TransformDataComponent(BaseComponent):
    """Transforms fetched data."""

    def process(self, context: FlowContext) -> FlowContext:
        fetch_result = context.get("fetch_result", {})
        data = fetch_result.get("data", {})
        users = data.get("users", [])

        transformed = [u.upper() for u in users]
        context.set("transformed_users", transformed)
        print(f"  [TransformData] Transformed users: {transformed}")

        return context


class SaveDataComponent(BaseComponent):
    """Saves transformed data."""

    def process(self, context: FlowContext) -> FlowContext:
        users = context.get("transformed_users", [])
        context.set("saved", True)
        context.set("saved_count", len(users))
        print(f"  [SaveData] Saved {len(users)} users")
        return context


class NotifyErrorComponent(BaseComponent):
    """Handles error notification."""

    def process(self, context: FlowContext) -> FlowContext:
        fetch_result = context.get("fetch_result", {})
        error = fetch_result.get("error", "Unknown error")
        context.set("notification_sent", True)
        context.set("notification_message", f"Error occurred: {error}")
        print(f"  [NotifyError] Sent notification: {error}")
        return context


def run_flow(simulate_error: bool = False) -> None:
    """Run the conditional flow."""
    print(f"\n{'='*50}")
    print(f"Running with simulate_error={simulate_error}")
    print("=" * 50)

    # Load configuration
    config_path = Path(__file__).parent / "flows" / "conditional.yaml"
    config = ConfigLoader.load(config_path)

    # Create components
    components = {
        "fetch_data": FetchDataComponent("fetch_data"),
        "transform_data": TransformDataComponent("transform_data"),
        "save_data": SaveDataComponent("save_data"),
        "notify_error": NotifyErrorComponent("notify_error"),
    }

    # Create engine
    engine = FlowEngine(config, components)

    # Execute with context
    context = FlowContext()
    context.set("simulate_error", simulate_error)

    print("\n--- Executing Flow ---")
    result = engine.execute(context)

    # Show results
    print("\n--- Results ---")
    print(f"Executed components: {list(result.metadata.component_timings.keys())}")
    print(f"Skipped components: {result.metadata.skipped_components}")

    if result.get("saved"):
        print(f"Saved {result.get('saved_count')} users")
    if result.get("notification_sent"):
        print(f"Notification: {result.get('notification_message')}")


def main() -> None:
    """Run conditional flow examples."""
    print("FlowEngine Conditional Flow Example")
    print("=" * 50)

    # Run successful flow
    run_flow(simulate_error=False)

    # Run with error
    run_flow(simulate_error=True)

    print("\n" + "=" * 50)
    print("Conditional flow examples completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
