# Contributing

Thank you for your interest in contributing to FlowEngine! This guide will help you get started.

---

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- pip or poetry

### Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourorg/flowengine.git
cd flowengine

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Verify Installation

```bash
# Run tests
pytest tests/ -v

# Type checking
mypy src/flowengine

# Linting
ruff check src/ tests/
```

---

## Project Structure

```
flowengine/
├── src/flowengine/      # Source code
│   ├── core/            # Core execution engine
│   ├── config/          # Configuration and validation
│   ├── eval/            # Expression evaluation
│   ├── errors/          # Exception hierarchy
│   └── contrib/         # Contributed components
├── tests/               # Test files
│   ├── unit/            # Unit tests
│   └── integration/     # Integration tests
├── docs/                # Documentation
├── examples/            # Example scripts
└── pyproject.toml       # Project configuration
```

---

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/my-feature
```

### 2. Make Changes

Write your code following the project style:

- Use type hints for all public functions
- Write docstrings in Google style
- Keep functions focused and testable

### 3. Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=flowengine --cov-report=term-missing

# Run specific test file
pytest tests/unit/core/test_engine.py -v
```

### 4. Type Checking

```bash
mypy src/flowengine
```

### 5. Linting

```bash
# Check for issues
ruff check src/ tests/

# Auto-fix issues
ruff check src/ tests/ --fix
```

### 6. Commit and Push

```bash
git add .
git commit -m "Add my feature"
git push origin feature/my-feature
```

### 7. Create Pull Request

Open a pull request on GitHub with:

- Clear description of changes
- Reference to any related issues
- Test coverage for new functionality

---

## Code Style

### Type Hints

All public functions should have type hints:

```python
def process_data(
    items: list[dict[str, Any]],
    config: ProcessConfig,
) -> list[ProcessedItem]:
    """Process a list of items according to config."""
    ...
```

### Docstrings

Use Google-style docstrings:

```python
def validate_config(self) -> list[str]:
    """Validate the component configuration.

    Checks that all required configuration options are present
    and have valid values.

    Returns:
        A list of validation error messages. Empty if valid.

    Examples:
        >>> component = MyComponent("test")
        >>> component.init({"required_field": "value"})
        >>> errors = component.validate_config()
        >>> assert errors == []
    """
    ...
```

### Imports

Use `ruff` for import sorting:

```python
# Standard library
import ast
from datetime import datetime
from typing import Any, Optional

# Third-party
from pydantic import BaseModel

# Local
from flowengine.core.context import FlowContext
from flowengine.errors.exceptions import ComponentError
```

---

## Testing Guidelines

### Unit Tests

Test individual components in isolation:

```python
import pytest
from flowengine import BaseComponent, FlowContext

class TestMyComponent:
    def test_process_basic(self):
        component = MyComponent("test")
        component.init({"setting": "value"})

        context = FlowContext()
        context.set("input", "data")

        result = component.process(context)

        assert result.data.output == "expected"

    def test_process_with_error(self):
        component = MyComponent("test")
        component.init({})

        context = FlowContext()

        with pytest.raises(ComponentError):
            component.process(context)
```

### Integration Tests

Test complete flows:

```python
def test_complete_flow():
    config = ConfigLoader.from_dict({
        "name": "Test Flow",
        "version": "1.0",
        "components": [...],
        "flow": {"steps": [...]}
    })

    engine = FlowEngine(config, components)
    result = engine.execute()

    assert result.data.final_result == "expected"
    assert not result.metadata.has_errors
```

### Test Coverage

Aim for high test coverage:

```bash
pytest tests/ --cov=flowengine --cov-report=html
open htmlcov/index.html
```

---

## Adding a New Feature

### 1. Design

Consider:

- How does it fit with existing architecture?
- What's the public API?
- How will it be documented?

### 2. Implement

- Write the implementation
- Add comprehensive tests
- Update docstrings

### 3. Document

- Update relevant documentation
- Add examples if applicable
- Update API reference if needed

### 4. Submit

- Create a pull request
- Respond to feedback
- Ensure CI passes

---

## Adding a Contrib Component

1. Create the component in `src/flowengine/contrib/`:

```python
# src/flowengine/contrib/my_component.py
from flowengine import BaseComponent, FlowContext

class MyComponent(BaseComponent):
    """Description of what this component does."""

    def init(self, config: dict) -> None:
        super().init(config)
        # Parse configuration

    def process(self, context: FlowContext) -> FlowContext:
        # Implementation
        return context
```

2. Export in `src/flowengine/contrib/__init__.py`

3. Add tests in `tests/unit/contrib/test_my_component.py`

4. Document in `docs/api/contrib.md`

---

## Reporting Issues

### Bug Reports

Include:

- FlowEngine version
- Python version
- Minimal reproducible example
- Expected vs actual behavior
- Full error traceback

### Feature Requests

Include:

- Use case description
- Proposed API (if applicable)
- Any alternatives considered

---

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow

---

## Questions?

- Open a GitHub issue for questions
- Check existing issues for similar questions
- Review the documentation

Thank you for contributing!
