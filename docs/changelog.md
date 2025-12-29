# Changelog

All notable changes to FlowEngine are documented here.

For the full changelog, see [CHANGELOG.md](https://github.com/yourorg/flowengine/blob/main/CHANGELOG.md) in the repository.

---

## Version History

### [Unreleased]

### [0.1.0] - Initial Release

#### Added

- **Core Engine**
  - `FlowEngine` class for flow orchestration
  - `BaseComponent` abstract class for components
  - `FlowContext` for data passing between components
  - `DotDict` for attribute-style dictionary access
  - `ExecutionMetadata` for timing and error tracking

- **Configuration**
  - YAML-based flow configuration
  - `ConfigLoader` for loading and validating configs
  - Pydantic models for type-safe configuration
  - `ComponentRegistry` for dynamic component loading

- **Flow Types**
  - Sequential flows (all matching steps run)
  - Conditional flows (first-match branching)

- **Condition Evaluation**
  - Safe Python expression evaluation
  - AST-based security validation
  - Support for comparisons, logical operators, membership

- **Timeout Handling**
  - Cooperative timeout mode with `check_deadline()`
  - Hard async timeout mode with asyncio
  - Hard process timeout mode with process isolation
  - Strict deadline enforcement option

- **Error Handling**
  - `fail_fast` flow-level setting
  - Per-step `on_error` handling (fail, skip, continue)
  - Condition error handling modes
  - Comprehensive exception hierarchy

- **Contrib Components**
  - `LoggingComponent` for debugging
  - `HTTPComponent` for API calls (optional)

- **Context Serialization**
  - Full JSON serialization/deserialization
  - Round-trip context restore

---

## Versioning

FlowEngine follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Incompatible API changes
- **MINOR**: New functionality, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

---

## Migration Guides

Migration guides for major version upgrades will be added here as new versions are released.
