"""Tests for FlowEngine config loader module."""

import tempfile
from pathlib import Path

import pytest

from flowengine import ConfigLoader, ConfigurationError


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_load_from_file(self) -> None:
        """Test loading configuration from YAML file."""
        yaml_content = """
name: "Test Flow"
version: "1.0"

components:
  - name: test
    type: myapp.TestComponent
    config:
      key: value

flow:
  type: sequential
  steps:
    - component: test
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = ConfigLoader.load(f.name)

            assert config.name == "Test Flow"
            assert config.version == "1.0"
            assert len(config.components) == 1
            assert config.components[0].config == {"key": "value"}

            # Cleanup
            Path(f.name).unlink()

    def test_load_file_not_found(self) -> None:
        """Test loading from non-existent file raises error."""
        with pytest.raises(ConfigurationError, match="not found"):
            ConfigLoader.load("nonexistent.yaml")

    def test_load_invalid_yaml(self) -> None:
        """Test loading invalid YAML raises error."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write("invalid: yaml: content: [")
            f.flush()

            with pytest.raises(ConfigurationError, match="Invalid YAML"):
                ConfigLoader.load(f.name)

            Path(f.name).unlink()

    def test_loads_from_string(self) -> None:
        """Test loading configuration from YAML string."""
        yaml_str = """
name: "String Flow"
components:
  - name: comp
    type: myapp.Comp
flow:
  steps:
    - component: comp
"""
        config = ConfigLoader.loads(yaml_str)

        assert config.name == "String Flow"
        assert len(config.components) == 1

    def test_loads_invalid_yaml(self) -> None:
        """Test loads with invalid YAML raises error."""
        with pytest.raises(ConfigurationError, match="Invalid YAML"):
            ConfigLoader.loads("invalid: yaml: [")

    def test_from_dict(self) -> None:
        """Test loading configuration from dictionary."""
        data = {
            "name": "Dict Flow",
            "components": [
                {"name": "test", "type": "myapp.Test", "config": {}},
            ],
            "flow": {
                "steps": [{"component": "test"}],
            },
        }

        config = ConfigLoader.from_dict(data)

        assert config.name == "Dict Flow"
        assert len(config.components) == 1

    def test_from_dict_empty(self) -> None:
        """Test from_dict with None raises error."""
        with pytest.raises(ConfigurationError, match="empty"):
            ConfigLoader._validate(None)

    def test_from_dict_not_dict(self) -> None:
        """Test from_dict with non-dict raises error."""
        with pytest.raises(ConfigurationError, match="must be a dictionary"):
            ConfigLoader._validate("not a dict")

    def test_from_dict_validation_errors(self) -> None:
        """Test from_dict with invalid data raises error with details."""
        data = {
            "name": "Test",
            # Missing required fields
        }

        with pytest.raises(ConfigurationError) as exc_info:
            ConfigLoader.from_dict(data)

        assert "validation failed" in str(exc_info.value).lower()

    def test_load_with_all_features(self) -> None:
        """Test loading config with all features."""
        yaml_str = """
name: "Full Featured Flow"
version: "2.0"
description: "A flow with all features"

components:
  - name: fetcher
    type: myapp.FetchComponent
    config:
      url: "https://api.example.com"
      timeout: 30

  - name: processor
    type: myapp.ProcessComponent
    config:
      mode: fast

  - name: saver
    type: myapp.SaveComponent
    config:
      path: /data/output

flow:
  type: conditional
  settings:
    fail_fast: false
    timeout_seconds: 120

  steps:
    - component: fetcher
      description: "Fetch data from API"

    - component: processor
      description: "Process the data"
      condition: "context.data.fetcher.status == 'success'"

    - component: saver
      description: "Save processed data"
      condition: "context.data.processor is not None"
      on_error: continue
"""
        config = ConfigLoader.loads(yaml_str)

        assert config.name == "Full Featured Flow"
        assert config.version == "2.0"
        assert config.description == "A flow with all features"
        assert len(config.components) == 3
        assert config.flow.type == "conditional"
        assert config.settings.fail_fast is False
        assert config.settings.timeout_seconds == 120
        assert len(config.steps) == 3
        assert config.steps[1].condition is not None
        assert config.steps[2].on_error == "continue"

    def test_load_path_is_directory(self) -> None:
        """Test loading from directory path raises error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ConfigurationError, match="not a file"):
                ConfigLoader.load(tmpdir)

    def test_load_with_path_object(self) -> None:
        """Test loading with Path object."""
        yaml_content = """
name: "Path Test"
components:
  - name: test
    type: myapp.Test
flow:
  steps:
    - component: test
"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            f.write(yaml_content)
            f.flush()

            config = ConfigLoader.load(Path(f.name))
            assert config.name == "Path Test"

            Path(f.name).unlink()
