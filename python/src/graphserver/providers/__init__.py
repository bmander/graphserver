"""Graphserver Edge Providers

This module contains various edge provider implementations for the Graphserver
planning engine. Edge providers generate graph edges dynamically based on
different data sources and routing scenarios.
"""

from __future__ import annotations

__all__ = []

# Import available providers
try:
    from .osm import OSMNetworkProvider, OSMAccessProvider
    __all__.extend(["OSMNetworkProvider", "OSMAccessProvider"])
except ImportError:
    # OSM dependencies not installed
    pass

try:
    from .transit import TransitProvider
    __all__.extend(["TransitProvider"])
except ImportError:
    # Transit dependencies not installed or module not built
    pass
