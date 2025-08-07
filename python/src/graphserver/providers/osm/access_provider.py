"""OSM Access Provider

This module provides the OSMAccessProvider class for connecting arbitrary
geographic coordinates to the OSM network via bidirectional edges.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from graphserver.core import (
    CacheAwareEdgeProvider,
    Edge,
    GraphserverDataType,
    Vertex,
    VertexEdgePair,
)

if TYPE_CHECKING:
    from .data_source import OSMDataSource

logger = logging.getLogger(__name__)


class OSMAccessProvider(CacheAwareEdgeProvider):
    """OSM access provider for connecting vertices to the OSM network.

    This provider uses explicit linking to connect vertices bidirectionally with OSM
    nodes.
    Vertices must be linked using the link() method before they can generate edges.

    Supported vertex types:
    1. Coordinate vertices (with lat/lon) - can be linked to nearby OSM nodes
    2. OSM node vertices - return edges to all linked vertices
    3. Other vertices - can be linked using external coordinates

    The linking is time-agnostic: vertices with the same properties but different
    times will link to the same OSM node, with time preserved across transitions.
    """

    def __init__(
        self,
        data_source: OSMDataSource,
        *,
        search_radius_m: float = 100.0,
        max_nearby_nodes: int = 5,
    ) -> None:
        """Initialize OSM access provider.

        Args:
            data_source: OSM data source containing parsed OSM data
            search_radius_m: Search radius for finding nearby nodes from coordinates
            max_nearby_nodes: Maximum number of nearby nodes to consider
        """
        super().__init__()  # Initialize CacheAwareEdgeProvider
        self.data_source = data_source
        self.search_radius_m = search_radius_m
        self.max_nearby_nodes = max_nearby_nodes

        # Linked vertices: bidirectional mapping between vertices and OSM nodes
        self._linked_vertices: dict[int, list[Vertex]] = {}  # OSM node ID -> vertices
        self._vertex_to_osm_node: dict[int, int] = {}  # vertex hash -> OSM node ID

        logger.info(
            "OSM access provider ready: %d nodes, search radius %.1fm",
            len(self.data_source.nodes),
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

    def _get_identity_hash(
        self, vertex_data: Mapping[str, GraphserverDataType]
    ) -> int | None:
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
                float(vertex_data["lat"]), float(vertex_data["lon"])
            )
        else:
            return None

        # Convert string to stable unsigned integer hash
        return hash(hash_string) & 0xFFFFFFFFFFFFFFFF

    def _get_time_agnostic_hash(self, vertex: Vertex) -> int:
        """Generate hash for vertex excluding time property.

        This allows vertices with the same properties but different times
        to be linked to the same OSM node.

        Args:
            vertex: Vertex to hash

        Returns:
            Hash value based on all properties except time
        """
        # Create dictionary of all vertex data except time
        vertex_data = {k: v for k, v in vertex.items() if k != "time"}

        # Create stable hash from sorted items
        return hash(tuple(sorted(vertex_data.items())))

    def link(self, vertex: Vertex, lat: float, lon: float) -> None:
        """Link a vertex to the nearest OSM node at given coordinates.

        This creates a bidirectional connection between the vertex and the nearest
        OSM node. Subsequently, the access provider will expand edges between
        the vertex and the linked OSM node.

        The linking is time-agnostic: vertices with the same properties but
        different times will link to the same OSM node.

        Args:
            vertex: The vertex to link
            lat: Latitude of the coordinates to link to
            lon: Longitude of the coordinates to link to

        Raises:
            ValueError: If no OSM node is found within search radius
        """
        # Find nearest OSM node
        if self.data_source.spatial_index is not None:
            nearest_node = self.data_source.spatial_index.find_nearest_node(
                lat, lon, self.search_radius_m
            )
        else:
            nearby_nodes = self.data_source.get_nearby_nodes(
                lat, lon, self.search_radius_m
            )
            nearest_node = nearby_nodes[0] if nearby_nodes else None

        if nearest_node is None:
            msg = f"No OSM node found within {self.search_radius_m}m of ({lat}, {lon})"
            raise ValueError(msg)

        # Get time-agnostic vertex hash (excludes time property)
        vertex_hash = self._get_time_agnostic_hash(vertex)

        # Store bidirectional mapping
        self._vertex_to_osm_node[vertex_hash] = nearest_node.id

        # Create vertex template without time for storage
        vertex_template_data = {k: v for k, v in vertex.items() if k != "time"}
        vertex_template = Vertex(vertex_template_data)

        # Calculate and cache distance for this link
        from .spatial import calculate_distance

        distance_m = calculate_distance(lat, lon, nearest_node.lat, nearest_node.lon)

        # Store cached distance
        if not hasattr(self, "_link_distances"):
            self._link_distances = {}
        self._link_distances[vertex_hash] = distance_m

        if nearest_node.id not in self._linked_vertices:
            self._linked_vertices[nearest_node.id] = []

        # Check if this vertex template is already linked to avoid duplicates
        existing_templates = self._linked_vertices[nearest_node.id]
        is_duplicate = any(
            dict(template.items()) == vertex_template_data
            for template in existing_templates
        )

        if not is_duplicate:
            self._linked_vertices[nearest_node.id].append(vertex_template)

            # Invalidate cache for the OSM node to ensure new edges are discovered
            # Must use the same identity hash that the network provider would use
            osm_node_data = {"osm_node_id": nearest_node.id}
            identity_hash = self._get_identity_hash(osm_node_data)
            osm_node_vertex = Vertex(osm_node_data, hash_value=identity_hash)
            try:
                self.invalidate_vertex(osm_node_vertex)
            except ValueError:
                # Vertex not in cache yet, no need to invalidate
                pass

    def clear_links(self) -> None:
        """Clear all vertex-OSM node links."""
        self._linked_vertices.clear()
        self._vertex_to_osm_node.clear()
        if hasattr(self, "_link_distances"):
            self._link_distances.clear()

    def out_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate outgoing edges from a vertex (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing either linked coordinates or OSM node ID

        Returns:
            List of (target_vertex, edge) tuples
        """

        # Handle OSM node vertices - return edges to linked vertices
        if "osm_node_id" in vertex:
            return self._edges_to_linked_vertices(vertex)

        # Handle other linked vertices (without coordinates) - check if linked
        vertex_hash = self._get_time_agnostic_hash(vertex)
        if vertex_hash in self._vertex_to_osm_node:
            return self._edges_from_linked_vertex(vertex)

        # Unknown vertex type
        return []

    def in_edges(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate incoming edges to a vertex.

        For OSM access providers, incoming edges are the same as outgoing edges
        since access links are bidirectional.

        Args:
            vertex: Input vertex containing either linked coordinates or OSM node ID

        Returns:
            List of (source_vertex, edge) tuples
        """

        # Handle OSM node vertices - return edges to linked vertices
        if "osm_node_id" in vertex:
            return self._edges_to_linked_vertices(vertex)

        # Handle other linked vertices (without coordinates) - check if linked
        vertex_hash = self._get_time_agnostic_hash(vertex)
        if vertex_hash in self._vertex_to_osm_node:
            return self._edges_from_linked_vertex(vertex)

        # Unknown vertex type
        return []

    def _edges_from_linked_vertex(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from a linked coordinate vertex to its linked OSM node.

        Args:
            vertex: Vertex containing "lat" and "lon" keys that has been linked

        Returns:
            List of edges to the linked OSM node, or empty if not linked
        """
        # Check if this vertex is linked to an OSM node using time-agnostic hash
        vertex_hash = self._get_time_agnostic_hash(vertex)

        if vertex_hash not in self._vertex_to_osm_node:
            # Vertex is not linked - return no edges
            return []

        osm_node_id = self._vertex_to_osm_node[vertex_hash]

        # Check if the OSM node exists in our data
        if osm_node_id not in self.data_source.nodes:
            return []

        node = self.data_source.nodes[osm_node_id]

        # Get cached distance for this link
        if hasattr(self, "_link_distances") and vertex_hash in self._link_distances:
            distance_m = self._link_distances[vertex_hash]
        else:
            # Fallback: calculate distance if not cached
            # (shouldn't happen for properly linked vertices)
            from .spatial import calculate_distance

            if "lat" in vertex and "lon" in vertex:
                lat = float(vertex["lat"])
                lon = float(vertex["lon"])
            else:
                # Final fallback - use node coordinates (zero distance)
                lat, lon = node.lat, node.lon

            distance_m = calculate_distance(lat, lon, node.lat, node.lon)

        # Calculate walking time
        duration_s = distance_m / self.data_source.walking_profile.base_speed_ms

        # Create target vertex with OSM node information
        target_data = {
            "osm_node_id": node.id,
        }

        # Preserve time from origin vertex if present
        if "time" in vertex:
            target_data["time"] = vertex["time"]

        identity_hash = self._get_identity_hash(target_data)
        target_vertex = Vertex(target_data, hash_value=identity_hash)

        # Create edge with cost based on walking time
        edge = Edge(
            cost=duration_s,
            metadata={
                "edge_type": "linked_vertex_to_node",
                "distance_m": distance_m,
                "duration_s": duration_s,
                "osm_node_id": node.id,
            },
        )

        return [(target_vertex, edge)]

    def _edges_to_linked_vertices(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from OSM node to linked vertices.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to linked vertices
        """
        node_id = int(vertex["osm_node_id"])

        # Check if this node has any linked vertices
        if node_id not in self._linked_vertices:
            return []

        # Check if node exists in our data
        if node_id not in self.data_source.nodes:
            return []

        node = self.data_source.nodes[node_id]
        edges = []

        # Generate edges to all linked vertices for this node
        for linked_vertex_template in self._linked_vertices[node_id]:
            # Get cached distance for this template
            template_hash = self._get_time_agnostic_hash(linked_vertex_template)

            if (
                hasattr(self, "_link_distances")
                and template_hash in self._link_distances
            ):
                distance_m = self._link_distances[template_hash]
            else:
                # Fallback: calculate distance if not cached
                # (shouldn't happen for properly linked vertices)
                from .spatial import calculate_distance

                if "lat" in linked_vertex_template and "lon" in linked_vertex_template:
                    target_lat = float(linked_vertex_template["lat"])
                    target_lon = float(linked_vertex_template["lon"])
                else:
                    # Final fallback - use node coordinates (zero distance)
                    target_lat, target_lon = node.lat, node.lon

                distance_m = calculate_distance(
                    node.lat, node.lon, target_lat, target_lon
                )

            # Calculate walking time
            duration_s = distance_m / self.data_source.walking_profile.base_speed_ms

            # Create target vertex with time preserved from origin
            target_data = dict(linked_vertex_template.items())

            # Preserve time from origin OSM node vertex if present
            if "time" in vertex:
                target_data["time"] = vertex["time"]

            target_vertex = Vertex(target_data)

            # Create edge to linked vertex
            edge = Edge(
                cost=duration_s,
                metadata={
                    "edge_type": "node_to_linked_vertex",
                    "distance_m": distance_m,
                    "duration_s": duration_s,
                },
            )

            edges.append((target_vertex, edge))

        return edges

    def find_nearest_node(self, lat: float, lon: float) -> Vertex | None:
        """Find the nearest OSM node to given coordinates.

        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees

        Returns:
            Vertex for nearest node or None if no node found
        """
        if self.data_source.spatial_index is not None:
            node = self.data_source.spatial_index.find_nearest_node(
                lat, lon, self.search_radius_m
            )
        else:
            nearby_nodes = self.data_source.get_nearby_nodes(
                lat, lon, self.search_radius_m
            )
            node = nearby_nodes[0] if nearby_nodes else None

        if node is None:
            return None

        node_data: dict[str, GraphserverDataType] = {
            "osm_node_id": node.id,
            **node.tags,
        }
        identity_hash = self._get_identity_hash(node_data)
        return Vertex(node_data, hash_value=identity_hash)

    @property
    def node_count(self) -> int:
        """Get number of OSM nodes in the provider."""
        return self.data_source.node_count

    @property
    def way_count(self) -> int:
        """Get number of walkable OSM ways in the provider."""
        return self.data_source.way_count

    @property
    def edge_count(self) -> int:
        """Get number of walkable edges in the provider."""
        return self.data_source.way_count

    def seed_vertices(self, *, max_vertices: int | None = None) -> Sequence[Vertex]:
        """Return all linked access points as seed vertices for graph exploration.

        Returns all vertices that have been explicitly linked to OSM nodes via the
        link() method. These represent the access points that can connect external
        vertices to the OSM network.

        Args:
            max_vertices: Maximum number of vertices to return. If None (default),
                returns all linked access points. If 0, returns empty sequence.
                If positive integer, returns up to that many access points.

        Returns:
            Sequence of Vertex objects representing linked access points,
            limited to at most 'max_vertices' vertices if specified

        Note:
            This only returns vertices that have been explicitly linked using the
            link() method. To get all possible vertices, you must first link them.
        """
        vertices = []
        count = 0

        for linked_vertex_list in self._linked_vertices.values():
            for vertex in linked_vertex_list:
                # Check max limit
                if max_vertices is not None and count >= max_vertices:
                    return vertices

                vertices.append(vertex)
                count += 1

        return vertices
