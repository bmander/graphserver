"""OSM Edge Provider

This module provides the main OSMProvider class that implements the EdgeProvider
protocol for OpenStreetMap-based pedestrian pathfinding.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from graphserver.core import Edge, Vertex, VertexEdgePair

from .parser import OSMParser
from .spatial import SpatialIndex
from .types import WalkingProfile

logger = logging.getLogger(__name__)


class OSMProvider:
    """OpenStreetMap edge provider for pedestrian pathfinding.

    This provider supports two types of vertex inputs:
    1. Geographic coordinates: {"lat": float, "lon": float}
    2. OSM node references: {"osm_node_id": int}

    For coordinate inputs, it finds nearby OSM nodes and generates edges to them.
    For node inputs, it returns edges to all connected nodes in the walkable network.
    """

    def __init__(
        self,
        osm_file: str | Path,
        *,
        walking_profile: WalkingProfile | None = None,
        search_radius_m: float = 100.0,
        max_nearby_nodes: int = 5,
        build_index: bool = True,
    ) -> None:
        """Initialize OSM provider from an OSM file.

        Args:
            osm_file: Path to OSM XML or PBF file
            walking_profile: Configuration for pedestrian routing preferences
            search_radius_m: Search radius for finding nearby nodes from coordinates
            max_nearby_nodes: Maximum number of nearby nodes to consider
            build_index: Whether to build spatial index (recommended for performance)

        Raises:
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        self.osm_file = Path(osm_file)
        self.walking_profile = walking_profile or WalkingProfile()
        self.search_radius_m = search_radius_m
        self.max_nearby_nodes = max_nearby_nodes

        # Parse OSM data
        logger.info("Initializing OSM provider from %s", self.osm_file)
        self.parser = OSMParser(self.walking_profile)
        self.parser.parse_file(self.osm_file)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_index:
            self._build_spatial_index()

        logger.info(
            "OSM provider ready: %d nodes, %d ways, %d edges",
            len(self.parser.nodes),
            len(self.parser.ways),
            len(self.parser.edges),
        )

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM nodes")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.parser.nodes)

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing either coordinates or OSM node ID

        Returns:
            List of (target_vertex, edge) tuples
        """
        # Check if vertex contains geographic coordinates
        if "lat" in vertex and "lon" in vertex:
            return self._edges_from_coordinates(vertex)

        # Check if vertex contains OSM node ID
        if "osm_node_id" in vertex:
            return self._edges_from_node_id(vertex)

        # Unknown vertex type - return empty edges
        logger.warning("Unknown vertex type: %s", vertex)
        return []

    def _edges_from_coordinates(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from geographic coordinates.

        Args:
            vertex: Vertex containing "lat" and "lon" keys

        Returns:
            List of edges to nearby OSM nodes
        """
        lat = float(vertex["lat"])
        lon = float(vertex["lon"])

        # Find nearby OSM nodes
        if self.spatial_index is not None:
            # Use spatial index for efficient lookup
            nearby_results = self.spatial_index.find_nearest_nodes(
                lat, lon, self.search_radius_m, self.max_nearby_nodes
            )
            nearby_nodes = [node for node, _ in nearby_results]
        else:
            # Fallback to linear search (slower)
            nearby_nodes = self.parser.get_nearby_nodes(lat, lon, self.search_radius_m)
            nearby_nodes = nearby_nodes[: self.max_nearby_nodes]

        # Generate edges to nearby nodes
        edges = []
        for node in nearby_nodes:
            # Calculate distance from input coordinates to OSM node
            from .spatial import calculate_distance

            distance_m = calculate_distance(lat, lon, node.lat, node.lon)

            # Use base walking speed for coordinate-to-node edges
            duration_s = distance_m / self.walking_profile.base_speed_ms

            # Create target vertex with OSM node information
            target_vertex = Vertex(
                {
                    "osm_node_id": node.id,
                    "lat": node.lat,
                    "lon": node.lon,
                    **node.tags,  # Include any relevant OSM tags
                }
            )

            # Create edge with cost based on walking time
            edge = Edge(
                cost=duration_s,
                metadata={
                    "edge_type": "coordinate_to_node",
                    "distance_m": distance_m,
                    "duration_s": duration_s,
                    "osm_node_id": node.id,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def _edges_from_node_id(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from OSM node ID.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to connected OSM nodes
        """
        node_id = int(vertex["osm_node_id"])

        # Check if node exists in our data
        if node_id not in self.parser.nodes:
            logger.warning("OSM node %d not found in parsed data", node_id)
            return []

        # Get all outgoing edges from this node
        edges = []
        for osm_edge in self.parser.get_node_edges(node_id):
            target_node_id = osm_edge.to_node_id

            # Skip if target node doesn't exist
            if target_node_id not in self.parser.nodes:
                continue

            target_node = self.parser.nodes[target_node_id]

            # Create target vertex
            target_vertex = Vertex(
                {
                    "osm_node_id": target_node.id,
                    "lat": target_node.lat,
                    "lon": target_node.lon,
                    **target_node.tags,
                }
            )

            # Apply walking profile to get final cost
            way = self.parser.ways[osm_edge.way_id]
            final_cost = self.walking_profile.get_edge_cost(osm_edge, way)

            # Create edge
            edge = Edge(
                cost=final_cost,
                metadata={
                    "edge_type": "osm_way",
                    "way_id": osm_edge.way_id,
                    "distance_m": osm_edge.distance_m,
                    "duration_s": osm_edge.duration_s,
                    "highway": way.tags.get("highway", ""),
                    "from_node_id": osm_edge.from_node_id,
                    "to_node_id": osm_edge.to_node_id,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def get_node_by_id(self, node_id: int) -> Vertex | None:
        """Get a vertex representation of an OSM node by ID.

        Args:
            node_id: OSM node ID

        Returns:
            Vertex object or None if node not found
        """
        if node_id not in self.parser.nodes:
            return None

        node = self.parser.nodes[node_id]
        return Vertex(
            {"osm_node_id": node.id, "lat": node.lat, "lon": node.lon, **node.tags}
        )

    def find_nearest_node(self, lat: float, lon: float) -> Vertex | None:
        """Find the nearest OSM node to given coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees

        Returns:
            Vertex for nearest node or None if no node found
        """
        if self.spatial_index is not None:
            node = self.spatial_index.find_nearest_node(lat, lon, self.search_radius_m)
        else:
            nearby_nodes = self.parser.get_nearby_nodes(lat, lon, self.search_radius_m)
            node = nearby_nodes[0] if nearby_nodes else None

        if node is None:
            return None

        return Vertex(
            {"osm_node_id": node.id, "lat": node.lat, "lon": node.lon, **node.tags}
        )

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes in the provider."""
        return len(self.parser.nodes)

    @property
    def way_count(self) -> int:
        """Get number of walkable OSM ways in the provider."""
        return len(self.parser.ways)

    @property
    def edge_count(self) -> int:
        """Get number of walkable edges in the provider."""
        return len(self.parser.edges)
