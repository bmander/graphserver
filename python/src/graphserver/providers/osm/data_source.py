"""OSM Data Source

This module provides the OSMDataSource class for parsing and managing
OpenStreetMap data to be shared across multiple providers.
"""

from __future__ import annotations

import logging
from pathlib import Path

try:
    import osmium
except ImportError as e:
    msg = "PyOsmium is required for OSM parsing. Install with: pip install osmium"
    raise ImportError(msg) from e


from .spatial import SpatialIndex
from .types import OSMNode, OSMWay, WalkingProfile

logger = logging.getLogger(__name__)


class OSMHandler(osmium.SimpleHandler):
    """PyOsmium handler for extracting pedestrian-relevant OSM data."""

    def __init__(self) -> None:
        """Initialize the OSM handler."""
        super().__init__()
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        self._node_count = 0
        self._way_count = 0
        self._walkable_way_count = 0

    def node(self, n: osmium.Node) -> None:
        """Process an OSM node."""
        self._node_count += 1

        # Convert tags to dictionary
        tags = {tag.k: tag.v for tag in n.tags}

        # Store all nodes - we'll filter later based on way references
        node = OSMNode(id=n.id, lat=n.location.lat, lon=n.location.lon, tags=tags)
        self.nodes[n.id] = node

        if self._node_count % 10000 == 0:
            logger.debug("Processed %d nodes", self._node_count)

    def way(self, w: osmium.Way) -> None:
        """Process an OSM way."""
        self._way_count += 1

        # Convert tags to dictionary
        tags = {tag.k: tag.v for tag in w.tags}

        # Extract node references
        node_refs = [node.ref for node in w.nodes]

        if len(node_refs) < 2:
            return  # Skip ways with insufficient nodes

        way = OSMWay(id=w.id, node_refs=node_refs, tags=tags)

        # Only store walkable ways
        if way.is_walkable():
            self.ways[w.id] = way
            self._walkable_way_count += 1

        if self._way_count % 10000 == 0:
            logger.debug(
                "Processed %d ways (%d walkable)",
                self._way_count,
                self._walkable_way_count,
            )

    def relation(self, r: osmium.Relation) -> None:
        """Process an OSM relation (currently ignored for pedestrian routing)."""
        # For now, we ignore relations as they're not essential for basic
        # pedestrian routing
        # In the future, we could handle route relations or access restrictions


class OSMDataSource:
    """OSM data source for parsing and managing raw OSM data.

    This class handles parsing of OSM files and provides shared access
    to the raw parsed data (nodes and ways) and spatial indexing for multiple
    providers. Edge generation is handled by the individual providers.
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
            build_spatial_index: Whether to build spatial index (recommended for
                performance)

        Raises:
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        self.osm_file = Path(osm_file)
        self.walking_profile = walking_profile or WalkingProfile()
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}

        # Parse OSM data
        logger.info("Initializing OSM data source from %s", self.osm_file)
        self._parse_file(self.osm_file)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_spatial_index:
            self._build_spatial_index()

        logger.info(
            "OSM data source ready: %d nodes, %d ways",
            len(self.nodes),
            len(self.ways),
        )

    def _parse_file(self, osm_file: str | Path) -> None:
        """Parse an OSM file and extract pedestrian network data.

        Args:
            osm_file: Path to OSM XML or PBF file

        Raises:
            FileNotFoundError: If the OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        osm_path = Path(osm_file)
        if not osm_path.exists():
            msg = f"OSM file not found: {osm_path}"
            raise FileNotFoundError(msg)

        logger.info("Parsing OSM file: %s", osm_path)

        try:
            # Parse the OSM file
            handler = OSMHandler()
            handler.apply_file(str(osm_path))

            logger.info(
                "Parsed %d nodes, %d walkable ways",
                len(handler.nodes),
                len(handler.ways),
            )

            # Store parsed data
            self.nodes = handler.nodes
            self.ways = handler.ways

            # Filter nodes to only those referenced by walkable ways
            self._filter_referenced_nodes()

        except Exception as e:
            msg = f"Failed to parse OSM file: {e}"
            raise RuntimeError(msg) from e

    def _filter_referenced_nodes(self) -> None:
        """Filter nodes to only include those referenced by walkable ways."""
        referenced_node_ids = set()

        for way in self.ways.values():
            referenced_node_ids.update(way.node_refs)

        # Keep only referenced nodes
        filtered_nodes = {
            node_id: node
            for node_id, node in self.nodes.items()
            if node_id in referenced_node_ids
        }

        self.nodes = filtered_nodes
        logger.info("Filtered to %d referenced nodes", len(self.nodes))

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM nodes")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.nodes)

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes."""
        return len(self.nodes)

    @property
    def way_count(self) -> int:
        """Get number of walkable OSM ways."""
        return len(self.ways)

    def get_nearby_nodes(
        self, lat: float, lon: float, radius_m: float = 100.0
    ) -> list[OSMNode]:
        """Get OSM nodes within a given radius of coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters

        Returns:
            List of nearby OSM nodes sorted by distance
        """
        # Use spatial index if available for efficient search
        if self.spatial_index is not None:
            # spatial index returns (node, distance) tuples already sorted by distance
            results = self.spatial_index.find_nearest_nodes(
                lat, lon, radius_m, max_results=1000
            )
            return [node for node, _ in results]

        # Fallback to linear search if no spatial index
        from .spatial import calculate_distance

        nearby_nodes = []
        for node in self.nodes.values():
            distance = calculate_distance(lat, lon, node.lat, node.lon)
            if distance <= radius_m:
                nearby_nodes.append(node)

        # Sort by distance
        nearby_nodes.sort(key=lambda n: calculate_distance(lat, lon, n.lat, n.lon))
        return nearby_nodes

    def get_ways_for_node(self, node_id: int) -> list[OSMWay]:
        """Get all walkable ways that reference a specific node.

        Args:
            node_id: OSM node ID

        Returns:
            List of OSMWay objects that reference the given node
        """
        return [way for way in self.ways.values() if node_id in way.node_refs]
