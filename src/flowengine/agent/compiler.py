"""FlowCompiler — the agent-facing entry point for turning YAML into a verdict.

This is the function an agent calls in the generate → validate → repair loop::

    result = FlowCompiler.compile_yaml(yaml_text, registry=my_registry)
    if not result.valid:
        # result.errors is a list of coded, JSON-patchable FlowIssue objects
        ...apply repairs, retry...
    else:
        engine = FlowEngine.from_config(result.flow_config)

Unlike :class:`~flowengine.config.loader.ConfigLoader`, which raises a single
``ConfigurationError``, the compiler returns *all* problems at once as structured
:class:`~flowengine.agent.issues.FlowIssue` objects with stable codes, document
paths, "did you mean" suggestions, and JSON-patch repair hints.
"""

from __future__ import annotations

import difflib
from typing import Any, Optional

import yaml
from pydantic import ValidationError

from flowengine.agent.issues import (
    FlowIssue,
    IssueCode,
    JsonPatchOp,
    RepairSuggestion,
    dotted_to_pointer,
)
from flowengine.agent.semantic import validate_semantics
from flowengine.config.registry import ComponentRegistry, load_component_class
from flowengine.config.schema import FlowConfig
from flowengine.errors import ConfigurationError
from pydantic import BaseModel, Field


class CompileResult(BaseModel):
    """The structured outcome of compiling agent-generated YAML.

    Attributes:
        valid: True when there are no error-severity issues.
        flow_config: The validated config (None if schema validation failed).
        errors: Error-severity issues that block execution.
        warnings: Warning-severity issues (advisory; do not block).
        normalized_yaml: Canonical YAML rendering of the validated config.
    """

    model_config = {"arbitrary_types_allowed": True}

    valid: bool
    flow_config: Optional[FlowConfig] = None
    errors: list[FlowIssue] = Field(default_factory=list)
    warnings: list[FlowIssue] = Field(default_factory=list)
    normalized_yaml: Optional[str] = None

    @property
    def issues(self) -> list[FlowIssue]:
        """All issues, errors first."""
        return [*self.errors, *self.warnings]

    def to_dict(self) -> dict[str, Any]:
        """Render an agent-facing JSON payload."""
        return {
            "valid": self.valid,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "normalized_yaml": self.normalized_yaml,
        }


def _loc_to_path(loc: tuple[Any, ...]) -> str:
    """Convert a Pydantic error location tuple to a dotted/indexed path."""
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            if parts:
                parts[-1] = f"{parts[-1]}[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))
    return ".".join(parts)


def _classify_pydantic_error(err: dict[str, Any]) -> tuple[IssueCode, str]:
    """Map a Pydantic error dict to an IssueCode and refined message."""
    etype = err.get("type", "")
    msg = err.get("msg", "Invalid value")
    lowered = msg.lower()
    if etype == "missing":
        return IssueCode.MISSING_FIELD, "Required field is missing"
    if "undefined component" in lowered:
        return IssueCode.UNDEFINED_COMPONENT_REF, msg
    if "duplicate" in lowered:
        return IssueCode.DUPLICATE_NAME, msg
    if "not found in nodes" in lowered:
        return IssueCode.UNKNOWN_EDGE_NODE, msg
    return IssueCode.INVALID_VALUE, msg


def _repair_for(code: IssueCode, path: str, err: dict[str, Any]) -> Optional[RepairSuggestion]:
    """Produce a JSON-patch repair hint for common, mechanically-fixable issues."""
    if code is IssueCode.MISSING_FIELD:
        pointer = dotted_to_pointer(path)
        return RepairSuggestion(
            explanation=f"Add the required field at {path}.",
            yaml_patch=[JsonPatchOp(op="add", path=pointer, value=None)],
            confidence=0.4,
        )
    return None


class FlowCompiler:
    """Compile and validate agent-generated flow YAML into a structured verdict."""

    @staticmethod
    def compile_yaml(
        yaml_text: str,
        registry: Optional[ComponentRegistry] = None,
        known_components: Optional[list[str]] = None,
        policy: Optional[Any] = None,
    ) -> CompileResult:
        """Compile YAML text into a :class:`CompileResult`.

        Args:
            yaml_text: The candidate flow YAML.
            registry: Optional registry used for metadata resolution and
                unknown-component detection.
            known_components: Optional explicit allowlist of valid component
                types/names used for "did you mean" suggestions (in addition to
                the registry). Useful when components are symbolic.
            policy: Optional :class:`~flowengine.agent.policy.ExecutionPolicy`
                enforced statically; violations become compile errors.

        Returns:
            A :class:`CompileResult` with errors, warnings, and normalized YAML.
        """
        # 1. Parse YAML.
        try:
            data = yaml.safe_load(yaml_text)
        except yaml.YAMLError as e:
            return CompileResult(
                valid=False,
                errors=[
                    FlowIssue(
                        code=IssueCode.YAML_PARSE_ERROR,
                        severity="error",
                        path="",
                        message=f"YAML could not be parsed: {e}",
                        why="The document must be valid YAML before it can be validated.",
                    )
                ],
            )
        if not isinstance(data, dict):
            return CompileResult(
                valid=False,
                errors=[
                    FlowIssue(
                        code=IssueCode.SCHEMA_INVALID,
                        severity="error",
                        path="",
                        message="Top-level YAML must be a mapping (object).",
                    )
                ],
            )
        return FlowCompiler.compile_dict(
            data,
            registry=registry,
            known_components=known_components,
            policy=policy,
        )

    @staticmethod
    def compile_dict(
        data: dict[str, Any],
        registry: Optional[ComponentRegistry] = None,
        known_components: Optional[list[str]] = None,
        policy: Optional[Any] = None,
    ) -> CompileResult:
        """Compile an already-parsed dict (see :meth:`compile_yaml`)."""
        # 2. Schema validation.
        try:
            config = FlowConfig.model_validate(data)
        except ValidationError as exc:
            errors: list[FlowIssue] = []
            for err in exc.errors():
                path = _loc_to_path(err.get("loc", ()))
                code, message = _classify_pydantic_error(err)
                errors.append(
                    FlowIssue(
                        code=code,
                        severity="error",
                        path=path,
                        message=message,
                        repair=_repair_for(code, path, err),
                    )
                )
            return CompileResult(valid=False, errors=errors)

        # 3. Component existence / "did you mean" checks (needs a known universe).
        errors = FlowCompiler._check_known_components(
            config, registry, known_components
        )

        # 4. Semantic validation (ports, reachability, contract, risk).
        semantic = validate_semantics(config, registry=registry)
        errors.extend(i for i in semantic if i.is_error)
        warnings = [i for i in semantic if not i.is_error]

        # 5. Policy enforcement (sandbox), if a policy was supplied.
        if policy is not None:
            policy_issues = policy.evaluate(config, registry=registry)
            errors.extend(i for i in policy_issues if i.is_error)
            warnings.extend(i for i in policy_issues if not i.is_error)

        valid = len(errors) == 0
        normalized = _normalize(config) if valid else None
        return CompileResult(
            valid=valid,
            flow_config=config if valid else None,
            errors=errors,
            warnings=warnings,
            normalized_yaml=normalized,
        )

    @staticmethod
    def _check_known_components(
        config: FlowConfig,
        registry: Optional[ComponentRegistry],
        known_components: Optional[list[str]],
    ) -> list[FlowIssue]:
        """Flag component types that are neither registered, importable, nor known."""
        universe: set[str] = set(known_components or [])
        if registry is not None:
            universe.update(registry.list_registered())
        # If we have no universe to check against and no registry, we cannot
        # tell "unknown" from "symbolic" — skip to avoid false positives.
        if not universe and registry is None:
            return []

        issues: list[FlowIssue] = []
        for i, comp in enumerate(config.components):
            if comp.type in universe:
                continue
            if registry is not None and registry.get_class(comp.type) is not None:
                continue
            # Importable dotted path counts as known.
            if "." in comp.type:
                try:
                    load_component_class(comp.type)
                    continue
                except ConfigurationError:
                    pass
            close = difflib.get_close_matches(comp.type, sorted(universe), n=1, cutoff=0.6)
            suggestion = f"Did you mean '{close[0]}'?" if close else None
            repair = None
            if close:
                repair = RepairSuggestion(
                    explanation=f"Replace components[{i}].type with '{close[0]}'.",
                    yaml_patch=[
                        JsonPatchOp(
                            op="replace",
                            path=f"/components/{i}/type",
                            value=close[0],
                        )
                    ],
                    confidence=0.7,
                )
            issues.append(
                FlowIssue(
                    code=IssueCode.UNKNOWN_COMPONENT,
                    severity="error",
                    path=f"components[{i}].type",
                    message=f"Component type '{comp.type}' is not registered or importable.",
                    why="Unknown components cannot be instantiated at execution time.",
                    suggestion=suggestion,
                    repair=repair,
                )
            )
        return issues


def _normalize(config: FlowConfig) -> str:
    """Canonical YAML rendering of a validated config."""
    from flowengine.agent.normalize import normalize_config

    return normalize_config(config)
