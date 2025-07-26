"""OSM Access Provider

This module provides the OSMAccessProvider class for connecting arbitrary
geographic coordinates to the OSM network via bidirectional edges.
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


class OSMAccessProvider:
    """OSM access provider for connecting coordinates to the OSM network.

    This provider handles two types of vertices:
    1. Vertices with lat/lon coordinates - returns edges to nearby OSM nodes
    2. Vertices with OSM node IDs - returns edges to registered offramp points

    Offramp points can be registered at specific coordinates and will be returned
    when querying nearby OSM nodes.
    """

    def __init__(
        self,
        osm_file: str | Path | None = None,
        *,
        parser: OSMParser | None = None,
        walking_profile: WalkingProfile | None = None,
        search_radius_m: float = 100.0,
        max_nearby_nodes: int = 5,
        build_index: bool = True,
    ) -> None:
        """Initialize OSM access provider.

        Args:
            osm_file: Path to OSM XML or PBF file (if parser not provided)
            parser: Pre-initialized OSM parser (if osm_file not provided)
            walking_profile: Configuration for pedestrian routing preferences
            search_radius_m: Search radius for finding nearby nodes from coordinates
            max_nearby_nodes: Maximum number of nearby nodes to consider
            build_index: Whether to build spatial index (recommended for performance)

        Raises:
            ValueError: If neither osm_file nor parser is provided
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        self.walking_profile = walking_profile or WalkingProfile()
        self.search_radius_m = search_radius_m
        self.max_nearby_nodes = max_nearby_nodes

        # Offramp points: mapping from OSM node ID to list of offramp vertices
        self._offramp_points: dict[int, list[Vertex]] = {}

        if parser is not None:
            self.parser = parser
        elif osm_file is not None:
            logger.info("Initializing OSM access provider from %s", osm_file)
            self.parser = OSMParser(self.walking_profile)
            self.parser.parse_file(osm_file)
        else:
            msg = "Either osm_file or parser must be provided"
            raise ValueError(msg)

        # Build spatial index for efficient coordinate-based queries
        self.spatial_index: SpatialIndex | None = None
        if build_index:
            self._build_spatial_index()

        logger.info(
            "OSM access provider ready: %d nodes, search radius %.1fm",
            len(self.parser.nodes),
            self.search_radius_m,
        )

    def _create_coordinate_identity_hash(self, lat: float, lon: float) -> str:
        """Create identity hash for coordinate vertices.

        Rounds coordinates to ~1 meter precision for matching tolerance.

        Args:
            lat: Latitude
            lon: Longitude

        Returns:
            Identity hash string
        """
        # Round to 5 decimal places (~1 meter precision)
        rounded_lat = round(lat, 5)
        rounded_lon = round(lon, 5)
        return f"coord:{rounded_lat},{rounded_lon}"

    def _get_identity_hash(self, vertex_data: dict) -> int | None:
        """Generate identity hash for vertex data.

        Args:
            vertex_data: Dictionary of vertex data

        Returns:
            Identity hash value or None if no hashable identity found
        """
        # Prioritize OSM node ID over coordinates if both are present
        if "osm_node_id" in vertex_data:
            hash_string = f"osm:{vertex_data['osm_node_id']}"
        elif "lat" in vertex_data and "lon" in vertex_data:
            hash_string = self._create_coordinate_identity_hash(
                vertex_data["lat"], vertex_data["lon"]
            )
        else:
            return None

        # Convert string to stable unsigned integer hash
        return hash(hash_string) & 0xFFFFFFFFFFFFFFFF

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM access")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.parser.nodes)

    def register_offramp_point(
        self, lat: float, lon: float, offramp_vertex_data: dict | None = None
    ) -> None:
        """Register an offramp point at the given coordinates.

        Args:
            lat: Offramp point latitude
            lon: Offramp point longitude
            offramp_vertex_data: Additional data for the offramp vertex
        """
        # Create offramp vertex
        vertex_data = {"lat": lat, "lon": lon}
        if offramp_vertex_data:
            vertex_data.update(offramp_vertex_data)

        identity_hash = self._get_identity_hash(vertex_data)
        offramp_vertex = Vertex(vertex_data, hash_value=identity_hash)

        # Find nearby OSM nodes for this offramp point
        if self.spatial_index is not None:
            nearby_results = self.spatial_index.find_nearest_nodes(
                lat, lon, self.search_radius_m, self.max_nearby_nodes
            )
            nearby_nodes = [node for node, distance in nearby_results]
        else:
            nearby_nodes = self.parser.get_nearby_nodes(lat, lon, self.search_radius_m)
            nearby_nodes = nearby_nodes[: self.max_nearby_nodes]

        # Register this offramp vertex for all nearby OSM nodes
        for node in nearby_nodes:
            if node.id not in self._offramp_points:
                self._offramp_points[node.id] = []
            self._offramp_points[node.id].append(offramp_vertex)

    def clear_offramp_points(self) -> None:
        """Clear all registered offramp points."""
        self._offramp_points.clear()

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing either lat/lon coordinates or OSM node ID

        Returns:
            List of (target_vertex, edge) tuples
        """
        # Handle lat/lon vertices - return edges to nearby OSM nodes
        if "lat" in vertex and "lon" in vertex:
            return self._edges_from_coordinates(vertex)

        # Handle OSM node vertices - return edges to registered offramp points
        if "osm_node_id" in vertex:
            return self._edges_to_offramp_points(vertex)

        # Unknown vertex type
        return []

    def _edges_from_coordinates(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from coordinates to nearby OSM nodes.

        Args:
            vertex: Vertex containing "lat" and "lon" keys

        Returns:
            List of edges to nearby OSM nodes
        """
        lat = float(vertex["lat"])
        lon = float(vertex["lon"])

        # Find nearby OSM nodes
        if self.spatial_index is not None:
            nearby_results = self.spatial_index.find_nearest_nodes(
                lat, lon, self.search_radius_m, self.max_nearby_nodes
            )
            nearby_nodes = [(node, distance) for node, distance in nearby_results]
        else:
            nodes = self.parser.get_nearby_nodes(lat, lon, self.search_radius_m)
            nodes = nodes[: self.max_nearby_nodes]
            # Calculate distances
            from .spatial import calculate_distance

            nearby_nodes = [
                (node, calculate_distance(lat, lon, node.lat, node.lon))
                for node in nodes
            ]

        # Generate edges to nearby nodes
        edges = []
        for node, distance_m in nearby_nodes:
            # Use base walking speed for coordinate-to-node edges
            duration_s = distance_m / self.walking_profile.base_speed_ms

            # Create target vertex with OSM node information
            target_data = {
                "osm_node_id": node.id,
                "lat": node.lat,
                "lon": node.lon,
                **node.tags,  # Include any relevant OSM tags
            }
            identity_hash = self._get_identity_hash(target_data)
            target_vertex = Vertex(target_data, hash_value=identity_hash)

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

    def _edges_to_offramp_points(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from OSM node to registered offramp points.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to offramp vertices
        """
        node_id = int(vertex["osm_node_id"])

        # Check if this node has any registered offramp points
        if node_id not in self._offramp_points:
            return []

        # Check if node exists in our data
        if node_id not in self.parser.nodes:
            return []

        node = self.parser.nodes[node_id]
        edges = []

        # Generate edges to all registered offramp points for this node
        for offramp_vertex in self._offramp_points[node_id]:
            # Calculate distance to offramp point
            from .spatial import calculate_distance

            distance_m = calculate_distance(
                node.lat, node.lon, offramp_vertex["lat"], offramp_vertex["lon"]
            )

            # Calculate walking time
            duration_s = distance_m / self.walking_profile.base_speed_ms

            # Create edge to offramp vertex
            edge = Edge(
                cost=duration_s,
                metadata={
                    "edge_type": "node_to_offramp",
                    "distance_m": distance_m,
                    "duration_s": duration_s,
                    "from_osm_node_id": node_id,
                },
            )

            edges.append((offramp_vertex, edge))

        return edges

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

        node_data = {
            "osm_node_id": node.id,
            "lat": node.lat,
            "lon": node.lon,
            **node.tags,
        }
        identity_hash = self._get_identity_hash(node_data)
        return Vertex(node_data, hash_value=identity_hash)

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes in the provider."""
        return len(self.parser.nodes)
