"""Transit Edge Provider

This module provides edge provider implementations for GTFS transit data.
It supports pathfinding on transit networks using GTFS feeds.

The module provides a TransitProvider that handles:
- Connections from coordinates to nearby transit stops
- Boarding vehicles at stops based on schedules
- In-vehicle travel between stops
- Alighting from vehicles at stops
"""

from __future__ import annotations

try:
    from .provider import TransitProvider

    __all__ = ["TransitProvider"]
except ImportError:
    # Transit dependencies not installed
    __all__ = []
