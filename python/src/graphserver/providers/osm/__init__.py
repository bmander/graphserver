"""OpenStreetMap Edge Provider

This module provides an edge provider implementation for OpenStreetMap (OSM) data.
It supports pathfinding on pedestrian networks extracted from OSM XML files.
"""

from __future__ import annotations

try:
    from .provider import OSMProvider

    __all__ = ["OSMProvider"]
except ImportError:
    # OSM dependencies not installed
    __all__ = []
