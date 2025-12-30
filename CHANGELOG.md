# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2024-12-28

### Added

- Initial release
- `BaseComponent` abstract base class with lifecycle methods
- `FlowContext` data container with attribute-style access
- `DotDict` helper for nested dictionary access
- `FlowEngine` executor for running component flows
- `ConfigLoader` for loading YAML configurations
- Pydantic schemas for configuration validation
- `ConditionEvaluator` for safe expression evaluation
- `SafeASTValidator` for security validation
- Custom exception hierarchy
- Comprehensive test suite
- Documentation and examples

### Security

- Safe expression evaluation prevents code injection
- Restricted AST nodes prevent malicious code execution
- No access to Python builtins in condition evaluation

## [0.1.1] - 2025-12-28

### Added

- Documentation and examples https://flowengine.readthedocs.io