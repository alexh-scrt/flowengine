"""FlowEngine contributed components.

This module provides ready-to-use components for common tasks.

Components:
    LoggingComponent: Logs context data at configurable levels
    HTTPComponent: Makes HTTP requests (requires httpx)
"""

from flowengine.contrib.logging import LoggingComponent

# HTTPComponent is conditionally imported since it requires httpx
try:
    from flowengine.contrib.http import HTTPComponent

    __all__ = ["LoggingComponent", "HTTPComponent"]
except ImportError:
    __all__ = ["LoggingComponent"]
