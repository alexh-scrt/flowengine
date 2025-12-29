#!/usr/bin/env python3
"""First-match branching (conditional flow type) example.

This example demonstrates the "conditional" flow type:
1. Flow type is "conditional" - first-match branching (switch/case semantics)
2. Steps are evaluated in order until ONE matches
3. After the first matching step executes, the flow STOPS
4. Useful for routing, dispatch, or mutually exclusive branches

Compare with "sequential" flow type where ALL matching steps run.

Run this example:
    python examples/routing_flow.py
"""

from pathlib import Path

from flowengine import BaseComponent, ConfigLoader, FlowContext, FlowEngine


class UserRequestHandler(BaseComponent):
    """Handles user-related requests."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("handler", "user")
        context.set("response", {"message": "User request handled"})
        print("  [UserHandler] Processed user request")
        return context


class OrderRequestHandler(BaseComponent):
    """Handles order-related requests."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("handler", "order")
        context.set("response", {"message": "Order request handled"})
        print("  [OrderHandler] Processed order request")
        return context


class AdminRequestHandler(BaseComponent):
    """Handles admin requests."""

    def process(self, context: FlowContext) -> FlowContext:
        context.set("handler", "admin")
        context.set("response", {"message": "Admin request handled"})
        print("  [AdminHandler] Processed admin request")
        return context


class UnknownRequestHandler(BaseComponent):
    """Handles unknown request types (default fallback)."""

    def process(self, context: FlowContext) -> FlowContext:
        request_type = context.get("request_type", "unknown")
        context.set("handler", "unknown")
        context.set("response", {"message": f"Unknown request type: {request_type}"})
        print(f"  [UnknownHandler] Handled unknown request: {request_type}")
        return context


def run_flow(request_type: str) -> None:
    """Run the routing flow with a specific request type."""
    print(f"\n{'='*50}")
    print(f"Routing request_type='{request_type}'")
    print("=" * 50)

    # Load configuration
    config_path = Path(__file__).parent / "flows" / "routing.yaml"
    config = ConfigLoader.load(config_path)

    # Create components
    components = {
        "handle_user_request": UserRequestHandler("handle_user_request"),
        "handle_order_request": OrderRequestHandler("handle_order_request"),
        "handle_admin_request": AdminRequestHandler("handle_admin_request"),
        "handle_unknown_request": UnknownRequestHandler("handle_unknown_request"),
    }

    # Create engine
    engine = FlowEngine(config, components)

    # Execute with context
    context = FlowContext()
    context.set("request_type", request_type)

    print("\n--- Executing Flow ---")
    result = engine.execute(context)

    # Show results
    print("\n--- Results ---")
    print(f"Handler used: {result.get('handler')}")
    print(f"Response: {result.get('response')}")
    print(f"Executed: {list(result.metadata.component_timings.keys())}")
    print(f"Skipped: {result.metadata.skipped_components}")


def main() -> None:
    """Run routing flow examples."""
    print("FlowEngine First-Match Branching Example")
    print("=" * 50)
    print("\nFlow type 'conditional' uses first-match semantics:")
    print("- Evaluates steps in order")
    print("- Stops after FIRST matching step executes")
    print("- Like switch/case in other languages")

    # Test different request types
    run_flow("user")   # Routes to UserHandler
    run_flow("order")  # Routes to OrderHandler
    run_flow("admin")  # Routes to AdminHandler
    run_flow("other")  # Falls through to UnknownHandler

    print("\n" + "=" * 50)
    print("Routing flow examples completed!")
    print("=" * 50)


if __name__ == "__main__":
    main()
