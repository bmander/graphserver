"""Graphserver Edge Providers

This module contains various edge provider implementations for the Graphserver
planning engine. Edge providers generate graph edges dynamically based on
different data sources and routing scenarios.
"""

from __future__ import annotations

__all__ = []

# Import OSM providers if available
try:
    from .osm import OSMAccessProvider, OSMNetworkProvider
    __all__.extend(["OSMAccessProvider", "OSMNetworkProvider"])
except ImportError:
    pass

# Import transit providers if available  
try:
    from .transit import TransitProvider
    __all__.extend(["TransitProvider"])
except ImportError:
    pass
