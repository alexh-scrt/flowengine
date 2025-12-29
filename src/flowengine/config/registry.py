"""Component registry for dynamic component loading.

This module provides utilities for loading component classes from type paths
and validating that component instances match their declared types.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Optional

from flowengine.errors import ConfigurationError

if TYPE_CHECKING:
    from flowengine.core.component import BaseComponent


def load_component_class(type_path: str) -> type[BaseComponent]:
    """Load a component class from its type path.

    Args:
        type_path: Fully qualified class path (e.g., "myapp.components.MyComponent")

    Returns:
        The component class

    Raises:
        ConfigurationError: If the path is invalid, module not found,
                          class not found, or class is not a BaseComponent
    """
    if not type_path or "." not in type_path:
        raise ConfigurationError(
            f"Invalid component type path: '{type_path}'. "
            "Expected format: 'module.path.ClassName'"
        )

    # Split into module path and class name
    module_path, class_name = type_path.rsplit(".", 1)

    try:
        module = importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        raise ConfigurationError(
            f"Module not found: '{module_path}' (from type path '{type_path}')",
            details=[str(e)],
        ) from e
    except ImportError as e:
        raise ConfigurationError(
            f"Failed to import module: '{module_path}'",
            details=[str(e)],
        ) from e

    try:
        component_class = getattr(module, class_name)
    except AttributeError as e:
        raise ConfigurationError(
            f"Class '{class_name}' not found in module '{module_path}'",
            details=[str(e)],
        ) from e

    # Import BaseComponent here to avoid circular imports
    from flowengine.core.component import BaseComponent

    if not isinstance(component_class, type) or not issubclass(
        component_class, BaseComponent
    ):
        raise ConfigurationError(
            f"'{type_path}' is not a valid BaseComponent subclass"
        )

    return component_class


class ComponentRegistry:
    """Registry for component classes and instances.

    The registry allows:
    - Registering component classes by name
    - Creating instances from type paths
    - Validating instances match declared types

    Example:
        ```python
        registry = ComponentRegistry()

        # Register a class
        registry.register_class("my_component", MyComponent)

        # Create instance from registered class
        instance = registry.create("my_component", "instance_name")

        # Or create from type path
        instance = registry.create_from_path(
            "myapp.components.MyComponent",
            "instance_name"
        )
        ```
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._classes: dict[str, type[BaseComponent]] = {}

    def register_class(
        self,
        name: str,
        component_class: type[BaseComponent],
    ) -> None:
        """Register a component class.

        Args:
            name: Name to register the class under
            component_class: The component class to register

        Raises:
            ConfigurationError: If name already registered or class invalid
        """
        if name in self._classes:
            raise ConfigurationError(f"Component class already registered: '{name}'")

        from flowengine.core.component import BaseComponent

        if not isinstance(component_class, type) or not issubclass(
            component_class, BaseComponent
        ):
            raise ConfigurationError(
                f"'{component_class}' is not a valid BaseComponent subclass"
            )

        self._classes[name] = component_class

    def get_class(self, name: str) -> Optional[type[BaseComponent]]:
        """Get a registered component class by name.

        Args:
            name: Name of the registered class

        Returns:
            The component class, or None if not found
        """
        return self._classes.get(name)

    def create(self, name: str, instance_name: str) -> BaseComponent:
        """Create an instance from a registered class.

        Args:
            name: Name of the registered class
            instance_name: Name for the new instance

        Returns:
            New component instance

        Raises:
            ConfigurationError: If class not registered
        """
        component_class = self._classes.get(name)
        if not component_class:
            raise ConfigurationError(f"Component class not registered: '{name}'")

        return component_class(instance_name)

    def create_from_path(self, type_path: str, instance_name: str) -> BaseComponent:
        """Create an instance from a type path.

        Args:
            type_path: Fully qualified class path
            instance_name: Name for the new instance

        Returns:
            New component instance
        """
        component_class = load_component_class(type_path)
        return component_class(instance_name)

    def list_registered(self) -> list[str]:
        """List all registered class names.

        Returns:
            List of registered class names
        """
        return list(self._classes.keys())


def validate_component_type(
    component: BaseComponent,
    expected_type_path: str,
) -> Optional[str]:
    """Validate that a component instance matches its declared type path.

    Args:
        component: The component instance to validate
        expected_type_path: The declared type path from config

    Returns:
        Error message if validation fails, None if valid
    """
    if not expected_type_path:
        return None

    # Get the actual type path of the instance
    actual_class = type(component)
    actual_type_path = f"{actual_class.__module__}.{actual_class.__name__}"

    # Try to load the expected class
    try:
        expected_class = load_component_class(expected_type_path)
    except ConfigurationError:
        # If we can't load the expected class, just check if paths match
        # This allows for cases where the type path is symbolic/not installed
        if not actual_type_path.endswith(expected_type_path.split(".")[-1]):
            return (
                f"Component type mismatch: expected '{expected_type_path}', "
                f"got '{actual_type_path}'"
            )
        return None

    # Check if the actual instance is an instance of the expected class
    if not isinstance(component, expected_class):
        return (
            f"Component type mismatch: expected '{expected_type_path}', "
            f"got '{actual_type_path}'"
        )

    return None
