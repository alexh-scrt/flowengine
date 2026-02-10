"""FlowEngine graph executor.

This module provides the GraphExecutor class that executes graph-type flows
using topological ordering with port-based routing.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from flowengine.config.schema import FlowSettings, GraphEdgeConfig, GraphNodeConfig
from flowengine.core.component import BaseComponent
from flowengine.core.context import FlowContext
from flowengine.errors import (
    ComponentError,
    ConfigurationError,
    FlowExecutionError,
    FlowTimeoutError,
)

if TYPE_CHECKING:
    from flowengine.eval.evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class GraphExecutor:
    """Executes a graph-type flow using topological ordering with port-based routing.

    Key semantics:
    - Root nodes (no incoming edges) execute first — these are triggers/entry points
    - Port routing: When a component sets active_port, only matching edges propagate
    - Unreachable nodes: If no incoming edge was activated, the node is skipped
    - Completed nodes: Nodes in completed_nodes are skipped (for resume support)
    """

    def __init__(
        self,
        nodes: list[GraphNodeConfig],
        edges: list[GraphEdgeConfig],
        components: dict[str, BaseComponent],
        settings: FlowSettings,
        hooks: list[Any] | None = None,
    ) -> None:
        self._nodes = {n.id: n for n in nodes}
        self._edges = edges
        self._components = components
        self._settings = settings
        self._hooks = hooks or []

        # Adjacency structures (built lazily)
        self._forward: dict[str, list[GraphEdgeConfig]] = {}
        self._reverse: dict[str, list[GraphEdgeConfig]] = {}
        self._build_adjacency()

    def execute(self, context: FlowContext) -> FlowContext:
        """Execute the graph flow."""
        flow_start_time = time.time()

        # Get execution order
        order = self._topological_sort()

        # Track which nodes are reachable (activated by an incoming edge)
        # Root nodes are always reachable
        roots = set(self._find_roots())
        activated: set[str] = set(roots)

        for node_id in order:
            # Check flow-level timeout
            elapsed = time.time() - flow_start_time
            if self._settings.timeout_seconds:
                remaining = self._settings.timeout_seconds - elapsed
                if remaining <= 0:
                    raise FlowTimeoutError(
                        f"Flow timeout exceeded: {elapsed:.2f}s > "
                        f"{self._settings.timeout_seconds}s",
                        timeout=self._settings.timeout_seconds,
                        elapsed=elapsed,
                        flow_id=context.metadata.flow_id,
                        step=node_id,
                    )
            else:
                remaining = None

            node = self._nodes[node_id]

            # Skip already-completed nodes (resume support)
            # But still propagate activation to downstream nodes
            if node_id in context.metadata.completed_nodes:
                logger.debug(f"Skipping already-completed node: {node_id}")
                # Propagate unconditional edges (we don't know the port from before)
                reachable_targets = self._get_reachable_targets(node_id, None)
                activated.update(reachable_targets)
                continue

            # Skip unreachable nodes
            if node_id not in activated:
                logger.info(f"Skipping unreachable node: {node_id}")
                context.metadata.skipped_components.append(node.component)
                self._notify(
                    "on_node_skipped", node_id, node.component, "unreachable"
                )
                continue

            # Execute the node
            component = self._components.get(node.component)
            if not component:
                raise FlowExecutionError(
                    f"Component not found for node '{node_id}': {node.component}"
                )

            # Clear port before execution
            context.clear_port()

            self._notify("on_node_start", node_id, node.component, context)

            start_time = time.time()
            step_started_at = datetime.now(timezone.utc)

            try:
                # Set deadline for cooperative timeout
                if remaining is not None:
                    context.metadata.deadline = time.time() + remaining
                else:
                    context.metadata.deadline = None
                context.metadata.deadline_checked = False

                # Execute component
                component.setup(context)
                try:
                    context = component.process(context)
                finally:
                    component.teardown(context)
                    context.metadata.deadline = None

                node_elapsed = time.time() - start_time
                context.metadata.record_timing(
                    node.component, node_elapsed, step_started_at
                )
                self._notify(
                    "on_node_complete",
                    node_id,
                    node.component,
                    context,
                    node_elapsed,
                )

                logger.info(f"Completed node {node_id} in {node_elapsed:.3f}s")

            except (FlowTimeoutError,):
                node_elapsed = time.time() - start_time
                context.metadata.record_timing(
                    node.component, node_elapsed, step_started_at
                )
                raise
            except Exception as e:
                node_elapsed = time.time() - start_time
                context.metadata.record_timing(
                    node.component, node_elapsed, step_started_at
                )
                context.metadata.add_error(node.component, e)

                self._notify(
                    "on_node_error", node_id, node.component, e, context
                )

                logger.error(f"Error in node {node_id}: {e}")

                if node.on_error == "fail" or self._settings.fail_fast:
                    raise ComponentError(
                        component=node.component,
                        message=str(e),
                        original_error=e,
                    ) from e
                elif node.on_error == "skip":
                    context.metadata.skipped_components.append(node.component)
                    continue
                # on_error == "continue" falls through
            finally:
                context.metadata.deadline = None
                context.metadata.deadline_checked = False

            # Check for suspension — do NOT mark node as completed so it
            # re-runs on resume (e.g., HumanApproval re-processes with
            # resume_data to see the approval decision)
            if context.metadata.suspended:
                self._notify(
                    "on_flow_suspended",
                    node_id,
                    context.metadata.suspension_reason or "",
                    None,
                )
                return context

            # Mark node completed only after successful non-suspended execution
            context.metadata.completed_nodes.append(node_id)

            # Determine which downstream nodes to activate based on port
            active_port = context.get_active_port()
            reachable_targets = self._get_reachable_targets(node_id, active_port)
            activated.update(reachable_targets)

        return context

    def _build_adjacency(self) -> None:
        """Build forward (successors) and reverse (predecessors) adjacency lists."""
        for node_id in self._nodes:
            self._forward[node_id] = []
            self._reverse[node_id] = []

        for edge in self._edges:
            self._forward[edge.source].append(edge)
            self._reverse[edge.target].append(edge)

    def _find_roots(self) -> list[str]:
        """Find nodes with no incoming edges (entry points)."""
        return [
            node_id
            for node_id in self._nodes
            if len(self._reverse[node_id]) == 0
        ]

    def _topological_sort(self) -> list[str]:
        """Kahn's algorithm — returns execution order.

        Raises:
            ConfigurationError: If cycle detected.
        """
        in_degree: dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            in_degree[edge.target] += 1

        queue: deque[str] = deque()
        for nid, degree in in_degree.items():
            if degree == 0:
                queue.append(nid)

        order: list[str] = []
        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for edge in self._forward[node_id]:
                in_degree[edge.target] -= 1
                if in_degree[edge.target] == 0:
                    queue.append(edge.target)

        if len(order) != len(self._nodes):
            raise ConfigurationError(
                "Cycle detected in graph flow",
                details=[
                    f"Processed {len(order)} of {len(self._nodes)} nodes. "
                    f"Remaining nodes are part of a cycle."
                ],
            )

        return order

    def _get_reachable_targets(
        self, node_id: str, active_port: str | None
    ) -> list[str]:
        """Given a node and its active port, return which downstream nodes to activate.

        Rules:
        - Edges with port=None always activate (unconditional)
        - If node has port-specific edges and active_port is set:
          only edges matching active_port activate (plus unconditional)
        - If node has port-specific edges but no active_port:
          only unconditional edges activate
        - If node has no port-specific edges: all outgoing edges activate
        """
        outgoing = self._forward.get(node_id, [])
        if not outgoing:
            return []

        has_port_edges = any(e.port is not None for e in outgoing)

        targets: list[str] = []
        for edge in outgoing:
            if edge.port is None:
                # Unconditional edge always activates
                targets.append(edge.target)
            elif has_port_edges and active_port is not None:
                # Port-specific edge: only if matching active_port
                if edge.port == active_port:
                    targets.append(edge.target)
            elif not has_port_edges:
                # No port edges at all — everything activates
                targets.append(edge.target)

        return targets

    def _notify(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Notify all registered hooks."""
        for hook in self._hooks:
            fn = getattr(hook, method, None)
            if fn:
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass  # hooks must not break execution
