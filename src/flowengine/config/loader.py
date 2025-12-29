"""FlowEngine configuration loader.

This module provides the ConfigLoader class for loading and
validating flow configurations from YAML files or strings.
"""

from pathlib import Path
from typing import Any, Union

import yaml
from pydantic import ValidationError

from flowengine.config.schema import FlowConfig
from flowengine.errors import ConfigurationError


class ConfigLoader:
    """Loads and validates flow configurations.

    Supports loading from:
    - YAML files
    - YAML strings
    - Python dictionaries

    Example:
        ```python
        # From file
        config = ConfigLoader.load("flow.yaml")

        # From string
        yaml_str = '''
        name: "Test Flow"
        components:
          - name: test
            type: myapp.TestComponent
        flow:
          steps:
            - component: test
        '''
        config = ConfigLoader.loads(yaml_str)

        # From dictionary
        config = ConfigLoader.from_dict({
            "name": "Test Flow",
            "components": [...],
            "flow": {...}
        })
        ```
    """

    @staticmethod
    def load(path: Union[str, Path]) -> FlowConfig:
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Validated FlowConfig object

        Raises:
            ConfigurationError: If file cannot be read or parsed
        """
        path = Path(path)

        if not path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {path}",
                config_path=str(path),
            )

        if not path.is_file():
            raise ConfigurationError(
                f"Path is not a file: {path}",
                config_path=str(path),
            )

        try:
            content = path.read_text(encoding="utf-8")
        except OSError as e:
            raise ConfigurationError(
                f"Cannot read file: {e}",
                config_path=str(path),
            ) from e

        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML: {e}",
                config_path=str(path),
            ) from e

        return ConfigLoader._validate(data, str(path))

    @staticmethod
    def loads(yaml_string: str) -> FlowConfig:
        """Load configuration from a YAML string.

        Args:
            yaml_string: YAML content as string

        Returns:
            Validated FlowConfig object

        Raises:
            ConfigurationError: If YAML is invalid or validation fails
        """
        try:
            data = yaml.safe_load(yaml_string)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML: {e}") from e

        return ConfigLoader._validate(data)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> FlowConfig:
        """Load configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Validated FlowConfig object

        Raises:
            ConfigurationError: If validation fails
        """
        return ConfigLoader._validate(data)

    @staticmethod
    def _validate(
        data: Any,
        config_path: str | None = None,
    ) -> FlowConfig:
        """Validate configuration data.

        Args:
            data: Parsed configuration data
            config_path: Optional path for error messages

        Returns:
            Validated FlowConfig object

        Raises:
            ConfigurationError: If validation fails
        """
        if data is None:
            raise ConfigurationError(
                "Configuration is empty",
                config_path=config_path,
            )

        if not isinstance(data, dict):
            raise ConfigurationError(
                f"Configuration must be a dictionary, got {type(data).__name__}",
                config_path=config_path,
            )

        try:
            return FlowConfig.model_validate(data)
        except ValidationError as e:
            # Extract error messages
            errors = []
            for error in e.errors():
                loc = ".".join(str(x) for x in error["loc"])
                msg = error["msg"]
                errors.append(f"{loc}: {msg}")

            raise ConfigurationError(
                "Configuration validation failed",
                config_path=config_path,
                details=errors,
            ) from e
