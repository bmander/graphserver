"""OSM Data Parser

This module handles parsing OpenStreetMap XML files using PyOsmium and
extracting walkable pedestrian network data.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

try:
    import osmium
except ImportError as e:
    msg = "PyOsmium is required for OSM parsing. Install with: pip install pyosmium"
    raise ImportError(msg) from e

from .types import OSMEdge, OSMNode, OSMWay, WalkingProfile

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


class OSMParser:
    """Parser for extracting pedestrian network data from OSM files."""

    def __init__(self, walking_profile: WalkingProfile | None = None) -> None:
        """Initialize the OSM parser.

        Args:
            walking_profile: Configuration for pedestrian routing preferences
        """
        self.walking_profile = walking_profile or WalkingProfile()
        self.nodes: dict[int, OSMNode] = {}
        self.ways: dict[int, OSMWay] = {}
        self.edges: dict[tuple[int, int], OSMEdge] = {}

    def parse_file(self, osm_file: str | Path) -> None:
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

            # Generate edges from ways
            self._generate_edges()

            logger.info("Generated %d walkable edges", len(self.edges))

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

    def _generate_edges(self) -> None:
        """Generate walkable edges from OSM ways."""
        from .spatial import calculate_distance

        for way in self.ways.values():
            walking_speed = way.get_walking_speed()

            # Create edges between consecutive nodes in the way
            for i in range(len(way.node_refs) - 1):
                from_node_id = way.node_refs[i]
                to_node_id = way.node_refs[i + 1]

                # Skip if nodes are missing
                if from_node_id not in self.nodes or to_node_id not in self.nodes:
                    continue

                from_node = self.nodes[from_node_id]
                to_node = self.nodes[to_node_id]

                # Calculate edge distance and duration
                distance_m = calculate_distance(
                    from_node.lat, from_node.lon, to_node.lat, to_node.lon
                )
                duration_s = distance_m / walking_speed

                # Create forward edge
                edge_tags = {
                    "highway": way.tags.get("highway", ""),
                    "way_id": way.id,
                    "walking_speed": walking_speed,
                }

                forward_edge = OSMEdge(
                    from_node_id=from_node_id,
                    to_node_id=to_node_id,
                    way_id=way.id,
                    distance_m=distance_m,
                    duration_s=duration_s,
                    tags=edge_tags,
                )

                # Store forward edge
                self.edges[(from_node_id, to_node_id)] = forward_edge

                # Create reverse edge for bidirectional ways (most pedestrian ways are bidirectional)
                oneway = way.tags.get("oneway", "no")
                if oneway not in {"yes", "true", "1"}:
                    reverse_edge = OSMEdge(
                        from_node_id=to_node_id,
                        to_node_id=from_node_id,
                        way_id=way.id,
                        distance_m=distance_m,
                        duration_s=duration_s,
                        tags=edge_tags,
                    )
                    self.edges[(to_node_id, from_node_id)] = reverse_edge

    def get_node_edges(self, node_id: int) -> Iterator[OSMEdge]:
        """Get all outgoing edges from a specific node.

        Args:
            node_id: OSM node ID

        Yields:
            OSMEdge objects starting from the given node
        """
        for (from_id, to_id), edge in self.edges.items():
            if from_id == node_id:
                yield edge

    def get_nearby_nodes(
        self, lat: float, lon: float, radius_m: float = 100.0
    ) -> list[OSMNode]:
        """Get OSM nodes within a given radius of coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            radius_m: Search radius in meters

        Returns:
            List of nearby OSM nodes
        """
        from .spatial import calculate_distance

        nearby_nodes = []

        for node in self.nodes.values():
            distance = calculate_distance(lat, lon, node.lat, node.lon)
            if distance <= radius_m:
                nearby_nodes.append(node)

        # Sort by distance
        nearby_nodes.sort(key=lambda n: calculate_distance(lat, lon, n.lat, n.lon))

        return nearby_nodes
