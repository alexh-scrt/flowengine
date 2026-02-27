"""FlowEngine graph executor.

This module provides the GraphExecutor class that executes graph-type flows
using topological ordering with port-based routing, and cyclic graphs via
a ready-queue executor.
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
    MaxIterationsError,
)

if TYPE_CHECKING:
    from flowengine.eval.evaluator import ConditionEvaluator

logger = logging.getLogger(__name__)


class GraphExecutor:
    """Executes a graph-type flow using topological ordering with port-based routing.

    For DAG graphs, uses topological sort (Kahn's algorithm) for execution order.
    For cyclic graphs, uses a ready-queue executor with iteration limits.

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

        # Adjacency structures
        self._forward: dict[str, list[GraphEdgeConfig]] = {}
        self._reverse: dict[str, list[GraphEdgeConfig]] = {}
        self._build_adjacency()

        # Detect cycles at construction time
        self._has_cycles, self._back_edges = self._detect_cycles()
        self._back_edge_targets: set[str] = {
            target for _, target in self._back_edges
        }

    def execute(self, context: FlowContext) -> FlowContext:
        """Execute the graph flow.

        Dispatches to the DAG executor for acyclic graphs, or the cyclic
        executor for graphs containing cycles.
        """
        if self._has_cycles:
            return self._execute_cyclic(context)
        return self._execute_dag(context)

    def _execute_node(
        self,
        node_id: str,
        node: GraphNodeConfig,
        context: FlowContext,
        flow_start_time: float,
    ) -> FlowContext:
        """Execute a single node with full lifecycle.

        Handles: hooks (pre/post), timing, error policies,
        deadline checking, port clearing, setup/process/teardown.
        Used by both DAG and cyclic executors.

        Returns:
            Updated FlowContext after node execution.

        Raises:
            FlowTimeoutError: If flow timeout exceeded before node starts.
            ComponentError: If node fails and error policy is 'fail'.
        """
        component = self._components.get(node.component)
        if not component:
            raise FlowExecutionError(
                f"Component not found for node '{node_id}': {node.component}"
            )

        # Calculate remaining timeout
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
            # on_error == "continue" falls through
        finally:
            context.metadata.deadline = None
            context.metadata.deadline_checked = False

        return context

    def _execute_dag(self, context: FlowContext) -> FlowContext:
        """Execute a DAG flow using topological ordering.

        This is the original execute() logic, preserved unchanged for
        acyclic graphs.
        """
        flow_start_time = time.time()

        # Get execution order
        order = self._topological_sort()

        # Track which nodes are reachable (activated by an incoming edge)
        # Root nodes are always reachable
        roots = set(self._find_roots())
        activated: set[str] = set(roots)

        for node_id in order:
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
            context = self._execute_node(node_id, node, context, flow_start_time)

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

    def _execute_cyclic(self, context: FlowContext) -> FlowContext:
        """Execute a cyclic graph using a ready-queue executor.

        Uses a BFS-style ready queue. Iteration count increments each time
        execution re-enters a back-edge target. Stops when:
        - The ready queue is empty (natural termination via port routing)
        - max_iterations is exceeded (controlled by on_max_iterations policy)
        - A per-node max_visits limit is reached
        - Global timeout expires
        """
        flow_start_time = time.time()

        # Identify which nodes participate in cycles
        cycle_nodes = self._identify_cycle_nodes()

        # Find roots: nodes with no incoming non-back-edges
        roots = self._find_roots_for_cyclic()

        # Initialize or resume visit tracking
        visit_counts: dict[str, int] = dict(context.metadata.node_visit_counts)
        iteration = context.metadata.iteration_count

        # Build ready queue — on resume, start from suspended node
        ready_queue: deque[str] = deque()
        if context.metadata.suspended_at_node:
            # Resuming from suspension — re-enqueue the suspended node
            ready_queue.append(context.metadata.suspended_at_node)
        else:
            ready_queue.extend(roots)

        iter_start: float | None = None  # Track iteration start for duration

        while ready_queue:
            node_id = ready_queue.popleft()
            node = self._nodes[node_id]

            # 1. Check per-node visit limit
            effective_max = self._effective_max_visits(node_id)
            if visit_counts.get(node_id, 0) >= effective_max:
                continue  # This path is exhausted

            # 2. Check iteration limit (only at back-edge targets that have
            #    already been visited — first visit is not a "loop")
            if node_id in self._back_edge_targets and visit_counts.get(node_id, 0) > 0:
                # The previous iteration just completed
                iter_end = time.time()
                self._notify(
                    "on_iteration_complete", iteration, node_id, context,
                    iter_end - (iter_start if iter_start else flow_start_time),
                )

                iteration += 1
                context.metadata.iteration_count = iteration
                iter_start = time.time()

                # Fire iteration start hook
                self._notify("on_iteration_start", iteration, node_id, context)

                if iteration > self._settings.max_iterations:
                    self._handle_max_iterations(context, node_id, iteration)
                    break

            # 3. Execute the node
            context = self._execute_node(node_id, node, context, flow_start_time)

            # 4. Update visit tracking
            visit_counts[node_id] = visit_counts.get(node_id, 0) + 1
            context.metadata.node_visit_counts = dict(visit_counts)

            # 5. Handle suspension (checkpoint/resume)
            if context.metadata.suspended:
                self._notify(
                    "on_flow_suspended",
                    node_id,
                    context.metadata.suspension_reason or "",
                    None,
                )
                return context

            # 6. Track completion for non-cycle nodes only
            # Cycle-participating nodes use visit_counts, not completed_nodes
            if node_id not in cycle_nodes:
                context.metadata.completed_nodes.append(node_id)

            # 7. Enqueue downstream based on port routing
            active_port = context.get_active_port()
            for target in self._get_reachable_targets(node_id, active_port):
                ready_queue.append(target)

        # Fire on_iteration_complete for the final iteration (natural exit)
        if iteration > 0 and not context.metadata.suspended:
            iter_end = time.time()
            # Use the last back-edge target as entry node, or first root
            entry_node = (
                list(self._back_edge_targets)[0]
                if self._back_edge_targets else roots[0]
            )
            self._notify(
                "on_iteration_complete", iteration, entry_node, context,
                iter_end - (iter_start if iter_start else flow_start_time),
            )

        return context

    # ── Helper methods ──────────────────────────────────────────────────

    def _build_adjacency(self) -> None:
        """Build forward (successors) and reverse (predecessors) adjacency lists."""
        for node_id in self._nodes:
            self._forward[node_id] = []
            self._reverse[node_id] = []

        for edge in self._edges:
            self._forward[edge.source].append(edge)
            self._reverse[edge.target].append(edge)

    def _find_roots(self) -> list[str]:
        """Find nodes with no incoming edges (entry points for DAG)."""
        return [
            node_id
            for node_id in self._nodes
            if len(self._reverse[node_id]) == 0
        ]

    def _find_roots_for_cyclic(self) -> list[str]:
        """Find nodes with no incoming non-back-edges (entry points for cyclic graphs).

        A node is a root if it has no incoming edges, or if all its incoming
        edges are back-edges. This handles self-loops correctly: a self-looping
        node with no other incoming edges is still a root.
        """
        roots: list[str] = []
        for node_id in self._nodes:
            incoming = self._reverse.get(node_id, [])
            # Check if all incoming edges are back-edges
            non_back_incoming = [
                e for e in incoming
                if (e.source, e.target) not in self._back_edges
            ]
            if not non_back_incoming:
                roots.append(node_id)
        return roots

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

    def _detect_cycles(self) -> tuple[bool, set[tuple[str, str]]]:
        """Detect cycles and identify back-edges using DFS.

        Uses white/gray/black coloring:
        - white: unvisited
        - gray: currently in DFS stack (ancestor)
        - black: fully explored

        An edge to a gray node is a back-edge (creates a cycle).

        Returns:
            Tuple of (has_cycles, back_edges) where back_edges is a set of
            (source_id, target_id) tuples that create cycles.
        """
        white, gray, black = 0, 1, 2
        color: dict[str, int] = dict.fromkeys(self._nodes, white)
        back_edges: set[tuple[str, str]] = set()

        def dfs(node_id: str) -> None:
            color[node_id] = gray
            for edge in self._forward.get(node_id, []):
                target = edge.target
                if color[target] == gray:
                    # Back-edge: target is an ancestor in current DFS path
                    back_edges.add((node_id, target))
                elif color[target] == white:
                    dfs(target)
            color[node_id] = black

        for node_id in self._nodes:
            if color[node_id] == white:
                dfs(node_id)

        return (len(back_edges) > 0, back_edges)

    def _identify_cycle_nodes(self) -> set[str]:
        """Find all nodes that participate in any cycle.

        A node participates in a cycle if it lies on a path from a
        back-edge target back to a back-edge source (following forward edges).
        """
        if not self._back_edges:
            return set()

        cycle_nodes: set[str] = set()
        for source, target in self._back_edges:
            # Find all nodes on paths from target to source (the cycle body)
            # BFS from target, looking for source, through forward edges
            # (excluding the back-edge itself)
            visited: set[str] = set()
            queue: deque[str] = deque([target])
            parent: dict[str, str | None] = {target: None}

            while queue:
                current = queue.popleft()
                if current in visited:
                    continue
                visited.add(current)

                if current == source:
                    # Trace path from target to source — all nodes are cycle nodes
                    path_node: str | None = source
                    while path_node is not None:
                        cycle_nodes.add(path_node)
                        path_node = parent.get(path_node)
                    break

                for edge in self._forward.get(current, []):
                    # Don't follow this back-edge
                    if (edge.source, edge.target) in self._back_edges:
                        continue
                    if edge.target not in visited:
                        parent[edge.target] = current
                        queue.append(edge.target)

        return cycle_nodes

    def _effective_max_visits(self, node_id: str) -> int:
        """Return the effective visit limit for a node.

        Uses per-node max_visits if set, otherwise flow-level max_iterations.
        """
        node = self._nodes[node_id]
        if node.max_visits is not None:
            return node.max_visits
        return self._settings.max_iterations

    def _handle_max_iterations(
        self, context: FlowContext, node_id: str, iteration: int
    ) -> None:
        """Handle reaching max_iterations based on policy."""
        context.metadata.max_iterations_reached = True

        # Fire on_max_iterations hook before applying policy
        self._notify("on_max_iterations", self._settings.max_iterations, node_id, context)

        if self._settings.on_max_iterations == "fail":
            raise MaxIterationsError(
                f"Cycle at node '{node_id}' reached "
                f"max_iterations={self._settings.max_iterations}",
                max_iterations=self._settings.max_iterations,
                actual_iterations=iteration,
                cycle_entry_node=node_id,
                flow_id=context.metadata.flow_id,
            )
        elif self._settings.on_max_iterations == "warn":
            logger.warning(
                "Max iterations reached: node=%s max=%d actual=%d",
                node_id,
                self._settings.max_iterations,
                iteration,
            )
        # "exit" silently stops

    def _notify(self, method: str, *args: Any, **kwargs: Any) -> None:
        """Notify all registered hooks."""
        for hook in self._hooks:
            fn = getattr(hook, method, None)
            if fn:
                try:
                    fn(*args, **kwargs)
                except Exception:
                    pass  # hooks must not break execution
