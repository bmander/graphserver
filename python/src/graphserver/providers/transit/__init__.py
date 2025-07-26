"""Transit Edge Provider

This module provides edge provider implementations for GTFS transit data.
It supports pathfinding on public transit networks including buses, trains,
and other scheduled services.

The module provides:
- TransitProvider: Handles navigation through transit networks using GTFS data
"""

from __future__ import annotations

try:
    from .provider import TransitProvider

    __all__ = ["TransitProvider"]
except ImportError:
    # Transit dependencies not installed or module not built
    __all__ = []