"""OSM Data Source

This module provides the OSMDataSource class for parsing and managing
OpenStreetMap data to be shared across multiple providers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

from .parser import OSMParser
from .spatial import SpatialIndex
from .types import OSMEdge, OSMNode, OSMWay, WalkingProfile

logger = logging.getLogger(__name__)


class OSMDataSource:
    """OSM data source for parsing and managing OSM data.

    This class encapsulates the parsing of OSM files and provides shared access
    to the parsed data (nodes, ways, edges) and spatial indexing for multiple
    providers.
    """

    def __init__(
        self,
        osm_file: str | Path,
        *,
        walking_profile: WalkingProfile | None = None,
        build_spatial_index: bool = True,
    ) -> None:
        """Initialize OSM data source from an OSM file.

        Args:
            osm_file: Path to OSM XML or PBF file
            walking_profile: Configuration for pedestrian routing preferences
            build_spatial_index: Whether to build spatial index (recommended for performance)

        Raises:
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        self.osm_file = Path(osm_file)
        self.walking_profile = walking_profile or WalkingProfile()

        # Parse OSM data
        logger.info("Initializing OSM data source from %s", self.osm_file)
        self.parser = OSMParser(self.walking_profile)
        self.parser.parse_file(self.osm_file)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_spatial_index:
            self._build_spatial_index()

        logger.info(
            "OSM data source ready: %d nodes, %d ways, %d edges",
            len(self.parser.nodes),
            len(self.parser.ways),
            len(self.parser.edges),
        )

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM nodes")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.parser.nodes)

    @property
    def nodes(self) -> Mapping[int, OSMNode]:
        """Get OSM nodes mapping."""
        return self.parser.nodes

    @property
    def ways(self) -> Mapping[int, OSMWay]:
        """Get OSM ways mapping."""
        return self.parser.ways

    @property
    def edges(self) -> list[OSMEdge]:
        """Get OSM edges list."""
        return self.parser.edges

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes."""
        return len(self.parser.nodes)

    @property
    def way_count(self) -> int:
        """Get number of walkable OSM ways."""
        return len(self.parser.ways)

    @property
    def edge_count(self) -> int:
        """Get number of walkable edges."""
        return len(self.parser.edges)

    def get_node_edges(self, node_id: int) -> list[OSMEdge]:
        """Get all outgoing edges from a node.

        Args:
            node_id: OSM node ID

        Returns:
            List of edges originating from the node
        """
        return self.parser.get_node_edges(node_id)

    def get_nearby_nodes(
        self, lat: float, lon: float, radius_m: float
    ) -> list[OSMNode]:
        """Get nodes within radius of coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters

        Returns:
            List of nodes within radius
        """
        return self.parser.get_nearby_nodes(lat, lon, radius_m)
