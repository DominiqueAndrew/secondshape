"""SecondShape inverse salvage planner.

The public surface is intentionally small so the planner can be called by a
CLI, an HTTP adapter, or tests without bringing in a web framework.
"""

from .engine import demo_request, solve, validate_plan

__all__ = ["demo_request", "solve", "validate_plan"]
