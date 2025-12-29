"""FlowEngine core module.

Provides the fundamental abstractions for flow execution:
- BaseComponent: Abstract base class for all components
- FlowContext: Context object passed through all components
- DotDict: Dictionary with attribute-style access
- FlowEngine: Orchestrates flow execution
"""

from flowengine.core.component import BaseComponent
from flowengine.core.context import DotDict, ExecutionMetadata, FlowContext
from flowengine.core.engine import FlowEngine

__all__ = [
    "BaseComponent",
    "FlowContext",
    "DotDict",
    "ExecutionMetadata",
    "FlowEngine",
]
