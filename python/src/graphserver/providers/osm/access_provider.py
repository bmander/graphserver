"""OSM Access Provider

This module provides the OSMAccessProvider class for connecting arbitrary
geographic coordinates to the OSM network via bidirectional edges.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from graphserver.core import Edge, Vertex, VertexEdgePair

from .parser import OSMParser
from .spatial import SpatialIndex
from .types import WalkingProfile

logger = logging.getLogger(__name__)


@dataclass
class AccessPoint:
    """Represents a registered access point with cached nearby OSM nodes."""

    id: str
    lat: float
    lon: float
    nearby_nodes: list[tuple[object, float]]  # (node, distance) pairs
    vertex: Vertex


class OSMAccessProvider:
    """OSM access provider for connecting registered access points to the OSM network.

    This provider handles bidirectional connections between registered access points
    and nearby OSM nodes. It generates both "onramp" edges (access point to OSM nodes)
    and "offramp" edges (OSM nodes to access points).

    Access points must be registered using register_access_point() before they can be
    used in routing queries. Each access point gets a unique ID and caches nearby OSM
    nodes for performance.
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

        # Access points with cached nearby nodes
        self._access_points: dict[str, AccessPoint] = {}
        self._access_point_counter = 0

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

    def _add_identity_hash(self, vertex_data: dict) -> dict:
        """Add identity hash to vertex data.

        Args:
            vertex_data: Dictionary of vertex data

        Returns:
            Updated vertex data with identity hash
        """
        # Prioritize OSM node ID over coordinates if both are present
        if "osm_node_id" in vertex_data:
            vertex_data["_id_hash"] = f"osm:{vertex_data['osm_node_id']}"
        elif "lat" in vertex_data and "lon" in vertex_data:
            vertex_data["_id_hash"] = self._create_coordinate_identity_hash(
                vertex_data["lat"], vertex_data["lon"]
            )

        return vertex_data

    def _build_spatial_index(self) -> None:
        """Build spatial index for fast coordinate-based lookups."""
        logger.info("Building spatial index for OSM access")
        self.spatial_index = SpatialIndex()
        self.spatial_index.add_nodes(self.parser.nodes)

    def register_access_point(self, lat: float, lon: float) -> str:
        """Register an access point and return its unique ID.

        Args:
            lat: Access point latitude
            lon: Access point longitude

        Returns:
            Unique access point ID
        """
        # Generate unique access point ID
        self._access_point_counter += 1
        access_point_id = f"ap_{self._access_point_counter:03d}"

        # Find nearby OSM nodes and cache them
        if self.spatial_index is not None:
            nearby_results = self.spatial_index.find_nearest_nodes(
                lat, lon, self.search_radius_m, self.max_nearby_nodes
            )
            nearby_nodes = [(node, distance) for node, distance in nearby_results]
        else:
            nodes = self.parser.get_nearby_nodes(lat, lon, self.search_radius_m)
            nodes = nodes[: self.max_nearby_nodes]
            # Calculate distances for caching
            from .spatial import calculate_distance

            nearby_nodes = [
                (node, calculate_distance(lat, lon, node.lat, node.lon))
                for node in nodes
            ]

        # Create vertex for this access point
        vertex_data = {"lat": lat, "lon": lon, "access_point_id": access_point_id}
        vertex = Vertex(self._add_identity_hash(vertex_data))

        # Create and store access point
        access_point = AccessPoint(
            id=access_point_id,
            lat=lat,
            lon=lon,
            nearby_nodes=nearby_nodes,
            vertex=vertex,
        )
        self._access_points[access_point_id] = access_point

        return access_point_id

    def get_access_point(self, access_point_id: str) -> AccessPoint | None:
        """Get access point by ID.

        Args:
            access_point_id: Access point ID

        Returns:
            AccessPoint object or None if not found
        """
        return self._access_points.get(access_point_id)

    def get_access_point_vertex(self, access_point_id: str) -> Vertex | None:
        """Get vertex for an access point by ID.

        Args:
            access_point_id: Access point ID

        Returns:
            Vertex for the access point or None if not found
        """
        access_point = self._access_points.get(access_point_id)
        return access_point.vertex if access_point else None

    def list_access_points(self) -> list[str]:
        """List all registered access point IDs.

        Returns:
            List of access point IDs
        """
        return list(self._access_points.keys())

    def remove_access_point(self, access_point_id: str) -> bool:
        """Remove an access point by ID.

        Args:
            access_point_id: Access point ID to remove

        Returns:
            True if access point was removed, False if not found
        """
        if access_point_id in self._access_points:
            del self._access_points[access_point_id]
            return True
        return False

    def clear_access_points(self) -> None:
        """Clear all registered access points."""
        self._access_points.clear()
        self._access_point_counter = 0

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing access point ID or OSM node ID

        Returns:
            List of (target_vertex, edge) tuples
        """
        # Handle OSM node inputs for offramp (OSM node -> access points)
        if "osm_node_id" in vertex:
            return self._offramp_edges_from_node(vertex)

        # Handle access point inputs (onramp: access point -> OSM nodes)
        if "access_point_id" in vertex:
            return self._edges_from_access_point(vertex)

        # Unknown vertex type
        return []

    def _edges_from_access_point(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate onramp edges from an access point to OSM nodes.

        Args:
            vertex: Vertex containing "access_point_id" key

        Returns:
            List of edges to nearby OSM nodes
        """
        access_point_id = vertex["access_point_id"]
        access_point = self._access_points.get(access_point_id)

        if access_point is None:
            return []

        # Generate edges to cached nearby nodes
        edges = []
        for node, distance_m in access_point.nearby_nodes:
            # Use base walking speed for access point-to-node edges
            duration_s = distance_m / self.walking_profile.base_speed_ms

            # Create target vertex with OSM node information
            target_data = {
                "osm_node_id": node.id,
                "lat": node.lat,
                "lon": node.lon,
                **node.tags,  # Include any relevant OSM tags
            }
            target_vertex = Vertex(self._add_identity_hash(target_data))

            # Create edge with cost based on walking time
            edge = Edge(
                cost=duration_s,
                metadata={
                    "edge_type": "access_point_to_node",
                    "distance_m": distance_m,
                    "duration_s": duration_s,
                    "osm_node_id": node.id,
                    "access_point_id": access_point_id,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def _offramp_edges_from_node(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate offramp edges from OSM nodes to nearby access points.

        This enables the planner to reach access point targets by providing
        edges from OSM nodes to access point vertices.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to access point vertices
        """
        node_id = int(vertex["osm_node_id"])

        # Check if node exists in our data
        if node_id not in self.parser.nodes:
            return []

        node = self.parser.nodes[node_id]

        # Generate offramps to all registered access points within range
        edges = []
        for access_point in self._access_points.values():
            # Calculate distance to access point
            from .spatial import calculate_distance

            distance_m = calculate_distance(
                node.lat, node.lon, access_point.lat, access_point.lon
            )

            # Only create offramp if access point is within reasonable range
            if distance_m <= self.search_radius_m:
                # Calculate walking time
                duration_s = distance_m / self.walking_profile.base_speed_ms

                # Create offramp edge to access point vertex
                edge = Edge(
                    cost=duration_s,
                    metadata={
                        "edge_type": "node_to_access_point",
                        "distance_m": distance_m,
                        "duration_s": duration_s,
                        "from_osm_node_id": node_id,
                        "access_point_id": access_point.id,
                    },
                )

                edges.append((access_point.vertex, edge))

        return edges

    def get_offramp_edges_to_access_point(
        self, node_id: int, access_point_id: str
    ) -> Sequence[VertexEdgePair]:
        """Generate offramp edges from an OSM node to a specific access point.

        Args:
            node_id: OSM node ID
            access_point_id: Target access point ID

        Returns:
            List containing edge to the access point if within range
        """
        if node_id not in self.parser.nodes:
            return []

        access_point = self._access_points.get(access_point_id)
        if access_point is None:
            return []

        node = self.parser.nodes[node_id]

        # Calculate distance to access point
        from .spatial import calculate_distance

        distance_m = calculate_distance(
            node.lat, node.lon, access_point.lat, access_point.lon
        )

        # Only create offramp if access point is within reasonable range
        if distance_m > self.search_radius_m:
            return []

        # Calculate walking time
        duration_s = distance_m / self.walking_profile.base_speed_ms

        # Create offramp edge
        edge = Edge(
            cost=duration_s,
            metadata={
                "edge_type": "node_to_access_point",
                "distance_m": distance_m,
                "duration_s": duration_s,
                "from_osm_node_id": node_id,
                "access_point_id": access_point_id,
            },
        )

        return [(access_point.vertex, edge)]

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
        return Vertex(self._add_identity_hash(node_data))

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes in the provider."""
        return len(self.parser.nodes)
