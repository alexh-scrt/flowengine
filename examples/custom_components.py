#!/usr/bin/env python3
"""Custom components example for FlowEngine.

This example demonstrates:
1. Creating components with configuration validation
2. Using setup/teardown for resource management
3. Error handling with on_error settings
4. Using the LoggingComponent for debugging

Run this example:
    python examples/custom_components.py
"""

import logging
from typing import Any

from flowengine import (
    BaseComponent,
    ComponentError,
    ConfigLoader,
    FlowContext,
    FlowEngine,
)
from flowengine.contrib.logging import LoggingComponent

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class DatabaseComponent(BaseComponent):
    """Component that simulates database operations.

    Demonstrates:
    - Configuration validation
    - Setup/teardown lifecycle
    - Resource management
    """

    def init(self, config: dict[str, Any]) -> None:
        super().init(config)
        self.connection_string = config.get("connection_string", "")
        self.table_name = config.get("table_name", "")
        self._connection: Any = None

    def validate_config(self) -> list[str]:
        """Validate required configuration."""
        errors = super().validate_config()
        if not self.connection_string:
            errors.append("connection_string is required")
        if not self.table_name:
            errors.append("table_name is required")
        return errors

    def setup(self, context: FlowContext) -> None:
        """Simulate opening database connection."""
        print(f"  [{self.name}] Opening connection to: {self.connection_string}")
        self._connection = {"connected": True, "table": self.table_name}

    def process(self, context: FlowContext) -> FlowContext:
        """Simulate database query."""
        if not self._connection:
            raise RuntimeError("Database not connected")

        # Simulate query result
        result = {
            "table": self.table_name,
            "rows": [
                {"id": 1, "name": "Item 1"},
                {"id": 2, "name": "Item 2"},
                {"id": 3, "name": "Item 3"},
            ],
        }
        context.set("db_result", result)
        print(f"  [{self.name}] Fetched {len(result['rows'])} rows from {self.table_name}")
        return context

    def teardown(self, context: FlowContext) -> None:
        """Close database connection."""
        if self._connection:
            print(f"  [{self.name}] Closing database connection")
            self._connection = None


class ValidationComponent(BaseComponent):
    """Component that validates data.

    Can be configured to fail for testing error handling.
    """

    def init(self, config: dict[str, Any]) -> None:
        super().init(config)
        self.required_fields = config.get("required_fields", [])
        self.fail_on_missing = config.get("fail_on_missing", True)

    def process(self, context: FlowContext) -> FlowContext:
        """Validate data has required fields."""
        db_result = context.get("db_result", {})
        rows = db_result.get("rows", [])

        if not rows:
            if self.fail_on_missing:
                raise ValueError("No data to validate")
            context.set("validation_result", {"valid": False, "reason": "No data"})
            return context

        # Check first row for required fields
        sample = rows[0]
        missing = [f for f in self.required_fields if f not in sample]

        if missing:
            result = {"valid": False, "missing_fields": missing}
            if self.fail_on_missing:
                raise ValueError(f"Missing required fields: {missing}")
        else:
            result = {"valid": True, "checked_fields": self.required_fields}

        context.set("validation_result", result)
        print(f"  [{self.name}] Validation result: {result}")
        return context


class ProcessorComponent(BaseComponent):
    """Component that processes validated data."""

    def init(self, config: dict[str, Any]) -> None:
        super().init(config)
        self.transform = config.get("transform", "none")

    def process(self, context: FlowContext) -> FlowContext:
        """Process the data based on configuration."""
        db_result = context.get("db_result", {})
        rows = db_result.get("rows", [])

        if self.transform == "uppercase":
            processed = [
                {**row, "name": row.get("name", "").upper()}
                for row in rows
            ]
        elif self.transform == "add_prefix":
            prefix = self.config.get("prefix", "ITEM_")
            processed = [
                {**row, "name": f"{prefix}{row.get('name', '')}"}
                for row in rows
            ]
        else:
            processed = rows

        context.set("processed_data", processed)
        print(f"  [{self.name}] Processed {len(processed)} items with transform={self.transform}")
        return context


def main() -> None:
    """Run the custom components example."""
    print("=" * 60)
    print("FlowEngine Custom Components Example")
    print("=" * 60)

    # Define flow configuration inline
    config = ConfigLoader.from_dict({
        "name": "Data Processing Pipeline",
        "version": "1.0",
        "description": "Demonstrates custom components with lifecycle methods",

        "components": [
            {
                "name": "db",
                "type": "examples.custom_components.DatabaseComponent",
                "config": {
                    "connection_string": "postgres://localhost/mydb",
                    "table_name": "items",
                },
            },
            {
                "name": "debug_after_db",
                "type": "flowengine.contrib.logging.LoggingComponent",
                "config": {
                    "level": "debug",
                    "message": "After database fetch",
                    "keys": ["db_result"],
                },
            },
            {
                "name": "validator",
                "type": "examples.custom_components.ValidationComponent",
                "config": {
                    "required_fields": ["id", "name"],
                    "fail_on_missing": False,
                },
            },
            {
                "name": "processor",
                "type": "examples.custom_components.ProcessorComponent",
                "config": {
                    "transform": "uppercase",
                },
            },
            {
                "name": "debug_final",
                "type": "flowengine.contrib.logging.LoggingComponent",
                "config": {
                    "level": "info",
                    "message": "Final state",
                    "log_metadata": True,
                },
            },
        ],

        "flow": {
            "type": "conditional",
            "settings": {
                "fail_fast": False,
                "timeout_seconds": 60,
            },
            "steps": [
                {
                    "component": "db",
                    "description": "Fetch data from database",
                },
                {
                    "component": "debug_after_db",
                    "description": "Debug: show fetched data",
                },
                {
                    "component": "validator",
                    "description": "Validate fetched data",
                    "condition": "context.data.db_result is not None",
                    "on_error": "continue",
                },
                {
                    "component": "processor",
                    "description": "Process validated data",
                    "condition": "context.data.validation_result.valid == True",
                },
                {
                    "component": "debug_final",
                    "description": "Debug: show final state",
                },
            ],
        },
    })

    # Create component instances
    components = {
        "db": DatabaseComponent("db"),
        "debug_after_db": LoggingComponent("debug_after_db"),
        "validator": ValidationComponent("validator"),
        "processor": ProcessorComponent("processor"),
        "debug_final": LoggingComponent("debug_final"),
    }

    # Create and validate engine
    engine = FlowEngine(config, components)

    errors = engine.validate()
    if errors:
        print(f"\nValidation errors: {errors}")
        return

    # Run dry run first
    print("\n--- Dry Run ---")
    dry_run_steps = engine.dry_run()
    print(f"Steps to execute: {dry_run_steps}")

    # Execute the flow
    print("\n--- Executing Flow ---")
    result = engine.execute()

    # Show results
    print("\n--- Final Results ---")
    print(f"Flow ID: {result.metadata.flow_id}")
    print(f"Duration: {result.metadata.total_duration:.4f}s")
    print(f"Executed: {list(result.metadata.component_timings.keys())}")
    print(f"Skipped: {result.metadata.skipped_components}")

    if result.get("processed_data"):
        print(f"\nProcessed data:")
        for item in result.get("processed_data", []):
            print(f"  - {item}")

    print("\n" + "=" * 60)
    print("Custom components example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
