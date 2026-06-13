"""Execution policy — the sandbox an agent-generated worker runs inside.

An agent may *generate* any YAML, but FlowEngine decides what is allowed to
*run*. An :class:`ExecutionPolicy` declares allow/deny lists, risk and approval
rules, and resource caps. It is enforced two ways:

* **Statically** (:meth:`ExecutionPolicy.evaluate`) — the primary gate. Run at
  compile time, it returns coded :class:`~flowengine.agent.issues.FlowIssue`
  errors for denied/non-allowlisted/high-risk/unapproved components and for
  configs whose iteration or call bounds exceed the policy.
* **At runtime** (:meth:`ExecutionPolicy.apply_to_config`) — tightens the flow's
  ``timeout_seconds`` / ``max_iterations`` so the engine's existing enforcement
  machinery honours the policy's resource caps.

(Hook callbacks cannot abort a run — the engine deliberately swallows hook
exceptions — so resource caps are enforced through settings, not a raising hook.)
"""

from __future__ import annotations

import copy
from typing import Optional

from pydantic import BaseModel, Field

from flowengine.agent.issues import FlowIssue, IssueCode, JsonPatchOp, RepairSuggestion
from flowengine.agent.meta import ComponentMeta
from flowengine.agent.semantic import build_meta_map
from flowengine.config.registry import ComponentRegistry
from flowengine.config.schema import FlowConfig


class ExecutionPolicy(BaseModel):
    """A sandbox policy for agent-generated flows."""

    max_runtime_seconds: Optional[float] = Field(
        default=None, description="Hard cap on total flow runtime."
    )
    max_iterations: Optional[int] = Field(
        default=None, description="Cap on cyclic-graph iterations."
    )
    max_component_calls: Optional[int] = Field(
        default=None, description="Cap on total component executions (acyclic)."
    )
    max_parallel_nodes: Optional[int] = Field(
        default=None, description="Advisory cap on concurrent nodes."
    )
    allowed_components: Optional[list[str]] = Field(
        default=None,
        description="Allowlist of component types/names. None = allow all.",
    )
    denied_components: list[str] = Field(
        default_factory=list, description="Denylist of component types/names."
    )
    require_approval_for: list[str] = Field(
        default_factory=list,
        description="Effects (see KNOWN_EFFECTS) that require explicit approval.",
    )
    approved: list[str] = Field(
        default_factory=list,
        description="Component names/types a human has pre-approved.",
    )
    allow_high_risk: bool = Field(
        default=False,
        description="If False, high/critical-risk components are rejected unless approved.",
    )

    # ── static enforcement ────────────────────────────────────────────────

    def evaluate(
        self,
        config: FlowConfig,
        registry: Optional[ComponentRegistry] = None,
        metas: Optional[dict[str, ComponentMeta]] = None,
    ) -> list[FlowIssue]:
        """Return policy-violation issues for ``config`` (empty == compliant)."""
        meta_map = metas or build_meta_map(config, registry=registry)
        issues: list[FlowIssue] = []

        for comp in config.components:
            ident = {comp.name, comp.type}
            approved = bool(ident & set(self.approved))

            if ident & set(self.denied_components):
                issues.append(
                    FlowIssue(
                        code=IssueCode.DENIED_COMPONENT,
                        severity="error",
                        path=f"components ({comp.name})",
                        message=f"Component '{comp.type}' is on the policy denylist.",
                        why="Denied components must never run in this sandbox.",
                    )
                )
                continue

            if self.allowed_components is not None and not (
                ident & set(self.allowed_components)
            ):
                issues.append(
                    FlowIssue(
                        code=IssueCode.NOT_ALLOWLISTED,
                        severity="error",
                        path=f"components ({comp.name})",
                        message=f"Component '{comp.type}' is not on the policy allowlist.",
                        why="Only allowlisted components may run in this sandbox.",
                        suggestion=f"Allowlisted: {self.allowed_components}",
                    )
                )
                continue

            meta = meta_map.get(comp.name)
            if meta is None or approved:
                continue

            needs_approval = bool(set(meta.effects) & set(self.require_approval_for))
            if needs_approval or meta.requires_approval:
                effects = sorted(set(meta.effects) & set(self.require_approval_for)) or meta.effects
                issues.append(
                    FlowIssue(
                        code=IssueCode.APPROVAL_REQUIRED,
                        severity="error",
                        path=f"components ({comp.name})",
                        message=(
                            f"Component '{comp.name}' requires approval "
                            f"(effects: {effects})."
                        ),
                        why="This effect is gated by policy until a human approves it.",
                        suggestion=f"Add '{comp.name}' to the policy's approved list.",
                    )
                )
            if meta.risk_level in ("high", "critical") and not self.allow_high_risk:
                issues.append(
                    FlowIssue(
                        code=IssueCode.RISK_EXCEEDS_POLICY,
                        severity="error",
                        path=f"components ({comp.name})",
                        message=(
                            f"Component '{comp.name}' is risk_level="
                            f"{meta.risk_level}, which exceeds policy."
                        ),
                        why="High-risk components are blocked unless explicitly allowed/approved.",
                    )
                )

        issues.extend(self._check_resource_caps(config))
        return issues

    def _check_resource_caps(self, config: FlowConfig) -> list[FlowIssue]:
        issues: list[FlowIssue] = []
        settings = config.flow.settings

        if (
            self.max_iterations is not None
            and settings.max_iterations > self.max_iterations
        ):
            issues.append(
                FlowIssue(
                    code=IssueCode.RISK_EXCEEDS_POLICY,
                    severity="error",
                    path="flow.settings.max_iterations",
                    message=(
                        f"max_iterations={settings.max_iterations} exceeds the "
                        f"policy limit of {self.max_iterations}."
                    ),
                    why="Cyclic flows must terminate within the policy's iteration budget.",
                    repair=RepairSuggestion(
                        explanation=f"Lower max_iterations to {self.max_iterations}.",
                        yaml_patch=[
                            JsonPatchOp(
                                op="replace",
                                path="/flow/settings/max_iterations",
                                value=self.max_iterations,
                            )
                        ],
                        confidence=0.9,
                    ),
                )
            )

        # For acyclic flows, the worst-case call count is the node/step count.
        if self.max_component_calls is not None:
            if config.flow.type == "graph":
                count = len(config.flow.nodes or [])
                cyclic = _graph_is_cyclic(config)
            else:
                count = len(config.flow.steps or [])
                cyclic = False
            if not cyclic and count > self.max_component_calls:
                issues.append(
                    FlowIssue(
                        code=IssueCode.RISK_EXCEEDS_POLICY,
                        severity="error",
                        path="flow",
                        message=(
                            f"Flow runs up to {count} components, exceeding the "
                            f"policy limit of {self.max_component_calls}."
                        ),
                        why="The flow could exceed the policy's component-call budget.",
                    )
                )
        return issues

    # ── runtime enforcement (via settings) ────────────────────────────────

    def apply_to_config(self, config: FlowConfig) -> FlowConfig:
        """Return a copy of ``config`` with settings tightened to the policy.

        Tightens ``timeout_seconds`` and ``max_iterations`` to the stricter of
        the existing value and the policy — these are the caps the engine
        actually enforces at runtime.
        """
        new = copy.deepcopy(config)
        settings = new.flow.settings
        if self.max_runtime_seconds is not None:
            settings.timeout_seconds = min(
                settings.timeout_seconds, self.max_runtime_seconds
            )
        if self.max_iterations is not None:
            settings.max_iterations = min(
                settings.max_iterations, self.max_iterations
            )
            # Stop gracefully rather than erroring when the loop hits the cap.
            if settings.on_max_iterations == "fail":
                settings.on_max_iterations = "exit"
        return new


def _graph_is_cyclic(config: FlowConfig) -> bool:
    from flowengine.core.graph import GraphExecutor

    executor = GraphExecutor(
        config.flow.nodes or [], config.flow.edges or [], {}, config.flow.settings
    )
    return executor._has_cycles
