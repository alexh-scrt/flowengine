#!/usr/bin/env python3
"""Timeout Modes Example.

This example demonstrates the three timeout enforcement modes in FlowEngine:
1. Cooperative mode (default) - components must call check_deadline()
2. Hard async mode - uses asyncio.wait_for for cancellation
3. Hard process mode - runs in separate process with hard kill

Run this example:
    python examples/timeout_modes.py
"""

import time

from flowengine import (
    BaseComponent,
    ConfigLoader,
    DeadlineCheckError,
    FlowConfig,
    FlowContext,
    FlowEngine,
    FlowTimeoutError,
)


class SlowComponent(BaseComponent):
    """Component that sleeps for a configured duration.

    This component does NOT call check_deadline(), simulating a
    non-cooperative component that could hang.
    """

    def init(self, config: dict) -> None:
        super().init(config)
        self.sleep_time = config.get("sleep_time", 2.0)

    def process(self, context: FlowContext) -> FlowContext:
        print(f"  [SlowComponent] Sleeping for {self.sleep_time}s...")
        time.sleep(self.sleep_time)
        context.set("slow_result", "completed")
        print("  [SlowComponent] Done!")
        return context


class CooperativeSlowComponent(BaseComponent):
    """Component that sleeps but cooperatively checks deadline.

    This component properly calls check_deadline() during long operations.
    """

    def init(self, config: dict) -> None:
        super().init(config)
        self.sleep_time = config.get("sleep_time", 2.0)
        self.check_interval = config.get("check_interval", 0.1)

    def process(self, context: FlowContext) -> FlowContext:
        print(f"  [CooperativeSlowComponent] Sleeping for {self.sleep_time}s...")
        elapsed = 0.0
        while elapsed < self.sleep_time:
            self.check_deadline(context)  # Cooperative timeout check
            time.sleep(self.check_interval)
            elapsed += self.check_interval
        context.set("cooperative_result", "completed")
        print("  [CooperativeSlowComponent] Done!")
        return context


def create_flow_config(
    timeout_mode: str = "cooperative",
    timeout_seconds: float = 1.0,
    require_deadline_check: bool = False,
) -> FlowConfig:
    """Create a flow configuration with specified timeout settings."""
    return FlowConfig(
        name=f"Timeout Mode Example ({timeout_mode})",
        version="1.0",
        description=f"Demonstrates {timeout_mode} timeout mode",
        components=[
            {"name": "slow", "type": "examples.timeout_modes.SlowComponent", "config": {"sleep_time": 2.0}},
        ],
        flow={
            "type": "sequential",
            "settings": {
                "timeout_seconds": timeout_seconds,
                "timeout_mode": timeout_mode,
                "require_deadline_check": require_deadline_check,
            },
            "steps": [{"component": "slow"}],
        },
    )


def demo_cooperative_mode() -> None:
    """Demonstrate cooperative mode - component can overrun timeout."""
    print("\n" + "=" * 60)
    print("COOPERATIVE MODE (default)")
    print("=" * 60)
    print("In this mode, components must call check_deadline() to respect timeouts.")
    print("A component that doesn't check will overrun the timeout.\n")

    config = create_flow_config(timeout_mode="cooperative", timeout_seconds=1.0)
    components = {"slow": SlowComponent("slow")}
    engine = FlowEngine(config, components, validate_types=False)

    context = FlowContext()
    start = time.time()

    try:
        result = engine.execute(context)
        elapsed = time.time() - start
        print(f"\nResult: {result.data.slow_result}")
        print(f"Elapsed: {elapsed:.2f}s (timeout was 1.0s)")
        print("Note: Component completed despite exceeding timeout!")
    except FlowTimeoutError as e:
        print(f"\nTimeout error: {e}")


def demo_cooperative_strict_mode() -> None:
    """Demonstrate cooperative mode with require_deadline_check=True."""
    print("\n" + "=" * 60)
    print("COOPERATIVE MODE (strict enforcement)")
    print("=" * 60)
    print("With require_deadline_check=True, components MUST call check_deadline().")
    print("Raises DeadlineCheckError if they don't.\n")

    config = create_flow_config(
        timeout_mode="cooperative",
        timeout_seconds=10.0,  # Long timeout so component completes
        require_deadline_check=True,
    )
    components = {"slow": SlowComponent("slow")}
    engine = FlowEngine(config, components, validate_types=False)

    context = FlowContext()

    try:
        result = engine.execute(context)
        print(f"\nComponent completed but didn't check deadline...")
    except DeadlineCheckError as e:
        print(f"\nDeadlineCheckError raised: {e.message}")
        print(f"Component '{e.component}' took {e.duration:.2f}s without checking deadline")


def demo_hard_async_mode() -> None:
    """Demonstrate hard_async mode - enforced timeout via asyncio."""
    print("\n" + "=" * 60)
    print("HARD ASYNC MODE")
    print("=" * 60)
    print("Uses asyncio.wait_for to enforce timeout.")
    print("Component will be interrupted even if it doesn't check deadline.\n")

    config = create_flow_config(timeout_mode="hard_async", timeout_seconds=1.0)
    components = {"slow": SlowComponent("slow")}
    engine = FlowEngine(config, components, validate_types=False)

    context = FlowContext()
    start = time.time()

    try:
        result = engine.execute(context)
        elapsed = time.time() - start
        print(f"\nResult: {result.data.slow_result}")
        print(f"Elapsed: {elapsed:.2f}s")
    except FlowTimeoutError as e:
        elapsed = time.time() - start
        print(f"\nTimeout enforced after {elapsed:.2f}s!")
        print(f"Error: {e.message}")


def demo_hard_process_mode() -> None:
    """Demonstrate hard_process mode - component runs in separate process."""
    print("\n" + "=" * 60)
    print("HARD PROCESS MODE")
    print("=" * 60)
    print("Runs component in separate process with hard kill on timeout.")
    print("Guarantees termination even for hung/infinite loops.\n")

    config = create_flow_config(timeout_mode="hard_process", timeout_seconds=1.0)
    components = {"slow": SlowComponent("slow")}
    engine = FlowEngine(config, components, validate_types=False)

    context = FlowContext()
    start = time.time()

    try:
        result = engine.execute(context)
        elapsed = time.time() - start
        print(f"\nResult: {result.data.slow_result}")
        print(f"Elapsed: {elapsed:.2f}s")
    except FlowTimeoutError as e:
        elapsed = time.time() - start
        print(f"\nTimeout enforced after {elapsed:.2f}s!")
        print(f"Error: {e.message}")


def demo_cooperative_with_compliant_component() -> None:
    """Demonstrate cooperative mode with a compliant component."""
    print("\n" + "=" * 60)
    print("COOPERATIVE MODE (with compliant component)")
    print("=" * 60)
    print("Shows a component that properly calls check_deadline().\n")

    config = FlowConfig(
        name="Cooperative Compliant Example",
        version="1.0",
        components=[
            {
                "name": "cooperative_slow",
                "type": "examples.timeout_modes.CooperativeSlowComponent",
                "config": {"sleep_time": 2.0, "check_interval": 0.1},
            },
        ],
        flow={
            "type": "sequential",
            "settings": {
                "timeout_seconds": 0.5,  # Short timeout
                "timeout_mode": "cooperative",
            },
            "steps": [{"component": "cooperative_slow"}],
        },
    )

    components = {"cooperative_slow": CooperativeSlowComponent("cooperative_slow")}
    engine = FlowEngine(config, components, validate_types=False)

    context = FlowContext()
    start = time.time()

    try:
        result = engine.execute(context)
        elapsed = time.time() - start
        print(f"\nResult: {result.data.cooperative_result}")
        print(f"Elapsed: {elapsed:.2f}s")
    except FlowTimeoutError as e:
        elapsed = time.time() - start
        print(f"\nTimeout detected at check_deadline() after {elapsed:.2f}s!")
        print(f"Error: {e.message}")
        print("This is the correct behavior for cooperative timeout!")


def main() -> None:
    """Run all timeout mode demonstrations."""
    print("=" * 60)
    print("FlowEngine Timeout Modes Example")
    print("=" * 60)
    print("\nThis example demonstrates three timeout enforcement modes:")
    print("1. cooperative - components must call check_deadline()")
    print("2. hard_async  - uses asyncio for enforced cancellation")
    print("3. hard_process - runs in separate process with hard kill")

    # Demo 1: Cooperative mode (component overruns)
    demo_cooperative_mode()

    # Demo 2: Cooperative mode with strict enforcement
    demo_cooperative_strict_mode()

    # Demo 3: Cooperative mode with compliant component
    demo_cooperative_with_compliant_component()

    # Demo 4: Hard async mode
    demo_hard_async_mode()

    # Demo 5: Hard process mode
    demo_hard_process_mode()

    print("\n" + "=" * 60)
    print("All demonstrations completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
