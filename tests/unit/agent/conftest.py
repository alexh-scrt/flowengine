"""Shared fixtures for agent-API tests: components that declare metadata."""

from flowengine.agent.meta import ComponentMeta, IOFieldSpec, PortSpec
from flowengine.core.component import BaseComponent
from flowengine.core.context import FlowContext


class SearchComponent(BaseComponent):
    """A low-risk producer of search_results from a query."""

    meta = ComponentMeta(
        name="web_search",
        description="Searches the web and returns ranked results.",
        inputs={"query": IOFieldSpec(type="string", required=True)},
        outputs={"search_results": IOFieldSpec(type="array")},
        ports=[PortSpec(name="success"), PortSpec(name="no_results")],
        tags=["search", "web"],
        cost="low",
        effects=["read_web"],
    )

    def process(self, context: FlowContext) -> FlowContext:
        context.set("search_results", ["r1", "r2"])
        return context


class SummarizeComponent(BaseComponent):
    """Consumes search_results, produces answer."""

    meta = ComponentMeta(
        name="llm_summarizer",
        description="Summarizes search results into an answer.",
        inputs={"search_results": IOFieldSpec(type="array", required=True)},
        outputs={"answer": IOFieldSpec(type="string")},
        ports=[PortSpec(name="done"), PortSpec(name="revise")],
        requires_llm=True,
        cost="medium",
    )

    def process(self, context: FlowContext) -> FlowContext:
        context.set("answer", "summary")
        return context


class ShellComponent(BaseComponent):
    """A high-risk component requiring approval."""

    meta = ComponentMeta(
        name="shell_exec",
        description="Executes a shell command.",
        risk_level="critical",
        effects=["execute_code", "modify_repo"],
        requires_approval=True,
    )

    def process(self, context: FlowContext) -> FlowContext:
        return context


class PlainComponent(BaseComponent):
    """A component with no metadata at all (the legacy/common case)."""

    def process(self, context: FlowContext) -> FlowContext:
        return context
