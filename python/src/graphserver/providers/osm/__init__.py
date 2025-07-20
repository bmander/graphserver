"""OpenStreetMap Edge Providers

This module provides edge provider implementations for OpenStreetMap (OSM) data.
It supports pathfinding on pedestrian networks extracted from OSM XML files.

The module provides two complementary providers:
- OSMNetworkProvider: Handles navigation between OSM nodes via streets/paths
- OSMAccessProvider: Handles connections between coordinates and the OSM network
"""

from __future__ import annotations

try:
    from .access_provider import OSMAccessProvider
    from .network_provider import OSMNetworkProvider

    __all__ = ["OSMNetworkProvider", "OSMAccessProvider"]
except ImportError:
    # OSM dependencies not installed
    __all__ = []
