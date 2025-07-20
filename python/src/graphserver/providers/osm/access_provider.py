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

from ...core import Edge, Vertex, VertexEdgePair
from .parser import OSMParser
from .spatial import SpatialIndex
from .types import WalkingProfile

logger = logging.getLogger(__name__)


class OSMAccessProvider:
    """OSM access provider for connecting coordinates to the OSM network.
    
    This provider handles bidirectional connections between arbitrary geographic
    coordinates and nearby OSM nodes. It generates both "onramp" edges (coordinate
    to OSM nodes) and "offramp" edges (OSM nodes to coordinates).
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

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM access")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.parser.nodes)

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing either coordinates or OSM node ID for offramp

        Returns:
            List of (target_vertex, edge) tuples
        """
        # Handle coordinate inputs (onramp: coordinate -> OSM nodes)
        if "lat" in vertex and "lon" in vertex:
            return self._edges_from_coordinates(vertex)

        # Handle OSM node inputs for offramp (OSM node -> coordinates)
        if "osm_node_id" in vertex:
            return self._offramp_edges_from_node(vertex)

        # Unknown vertex type
        return []

    def _edges_from_coordinates(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate onramp edges from geographic coordinates to OSM nodes.

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

    def _offramp_edges_from_node(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate offramp edges from OSM nodes to nearby coordinates.
        
        This enables the planner to reach arbitrary coordinate targets by providing
        edges from OSM nodes to coordinate vertices.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to coordinate vertices
        """
        node_id = int(vertex["osm_node_id"])

        # Check if node exists in our data
        if node_id not in self.parser.nodes:
            return []

        node = self.parser.nodes[node_id]

        # For offramps, we need to find target coordinates within range
        # In practice, this would be driven by the planner looking for paths to specific coordinates
        # For now, we return an empty list since offramps are created dynamically during planning
        # when the planner needs to reach a specific coordinate target

        # NOTE: This method will be called by the planner when it encounters an OSM node
        # and is looking for ways to reach coordinate-based goals. The actual implementation
        # would depend on the specific coordinate targets the planner is trying to reach.

        return []

    def get_offramp_edges_to_coordinate(
        self, node_id: int, target_lat: float, target_lon: float
    ) -> Sequence[VertexEdgePair]:
        """Generate offramp edges from an OSM node to a specific coordinate.
        
        This method is called when the planner needs to create an offramp from an OSM node
        to reach a specific coordinate target.

        Args:
            node_id: OSM node ID
            target_lat: Target latitude
            target_lon: Target longitude

        Returns:
            List containing edge to the target coordinate if within range
        """
        if node_id not in self.parser.nodes:
            return []

        node = self.parser.nodes[node_id]

        # Calculate distance to target coordinate
        from .spatial import calculate_distance
        distance_m = calculate_distance(node.lat, node.lon, target_lat, target_lon)

        # Only create offramp if target is within reasonable range
        if distance_m > self.search_radius_m:
            return []

        # Calculate walking time
        duration_s = distance_m / self.walking_profile.base_speed_ms

        # Create target vertex for the coordinate
        target_vertex = Vertex({"lat": target_lat, "lon": target_lon})

        # Create offramp edge
        edge = Edge(
            cost=duration_s,
            metadata={
                "edge_type": "node_to_coordinate",
                "distance_m": distance_m,
                "duration_s": duration_s,
                "from_osm_node_id": node_id,
            },
        )

        return [(target_vertex, edge)]

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
