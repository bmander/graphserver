"""OSM Network Provider

This module provides the OSMNetworkProvider class for navigation between
OSM nodes via the street/path network.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from graphserver.core import Edge, GraphserverDataType, Vertex, VertexEdgePair

from .data_source import OSMDataSource

logger = logging.getLogger(__name__)


class OSMNetworkProvider:
    """OSM network provider for navigation between OSM nodes.

    This provider handles movement between OSM nodes via the actual street/path
    network. It only accepts vertices with OSM node IDs and returns edges to
    connected nodes based on the walkable OSM ways.
    """

    def __init__(self, data_source: OSMDataSource) -> None:
        """Initialize OSM network provider.

        Args:
            data_source: OSM data source containing parsed OSM data
        """
        self.data_source = data_source

        logger.info(
            "OSM network provider ready: %d nodes, %d ways",
            len(self.data_source.nodes),
            len(self.data_source.ways),
        )

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
        else:
            return None

        # Convert string to stable unsigned integer hash
        return hash(hash_string) & 0xFFFFFFFFFFFFFFFF

    def __call__(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from an OSM node (implements EdgeProvider protocol).

        Args:
            vertex: Input vertex containing OSM node ID

        Returns:
            List of (target_vertex, edge) tuples to connected OSM nodes
        """
        # Only handle OSM node vertices
        if "osm_node_id" not in vertex:
            return []

        return self._edges_from_node_id(vertex)

    def _edges_from_node_id(self, vertex: Vertex) -> Sequence[VertexEdgePair]:
        """Generate edges from OSM node ID.

        Args:
            vertex: Vertex containing "osm_node_id" key

        Returns:
            List of edges to connected OSM nodes
        """
        node_id = int(vertex["osm_node_id"])

        # Check if node exists in our data
        if node_id not in self.data_source.nodes:
            logger.warning("OSM node %d not found in parsed data", node_id)
            return []

        # Generate edges dynamically from ways that include this node
        edges = []
        ways_for_node = self.data_source.get_ways_for_node(node_id)

        for way in ways_for_node:
            # Find this node's position in the way
            try:
                node_index = way.node_refs.index(node_id)
            except ValueError:
                continue  # Node not in this way (shouldn't happen)

            # Generate edges to adjacent nodes in the way
            for target_index in [node_index - 1, node_index + 1]:
                if target_index < 0 or target_index >= len(way.node_refs):
                    continue  # Out of bounds

                target_node_id = way.node_refs[target_index]

                # Skip if target node doesn't exist
                if target_node_id not in self.data_source.nodes:
                    continue

                # Check if this is a oneway that prevents this direction
                oneway = way.tags.get("oneway", "no")
                if oneway in {"yes", "true", "1"}:
                    # For oneway, only allow forward direction (increasing index)
                    if target_index < node_index:
                        continue

                target_node = self.data_source.nodes[target_node_id]
                from_node = self.data_source.nodes[node_id]

                # Calculate edge distance and cost
                from .spatial import calculate_distance

                distance_m = calculate_distance(
                    from_node.lat, from_node.lon, target_node.lat, target_node.lon
                )

                # Get walking speed for this way type
                walking_speed = way.get_walking_speed()
                duration_s = distance_m / walking_speed

                # Apply walking profile to get final cost
                walking_profile = self.data_source.walking_profile
                # Create a temporary edge-like object for the walking profile
                from .types import OSMEdge

                temp_edge = OSMEdge(
                    from_node_id=node_id,
                    to_node_id=target_node_id,
                    way_id=way.id,
                    distance_m=distance_m,
                    duration_s=duration_s,
                    tags={"highway": way.tags.get("highway", "")},
                )
                final_cost = walking_profile.get_edge_cost(temp_edge, way)

                # Create target vertex
                target_data = {
                    "osm_node_id": target_node.id,
                }
                # Create target vertex with identity hash
                identity_hash = self._get_identity_hash(target_data)
                target_vertex = Vertex(target_data, hash_value=identity_hash)

                # Create edge
                edge = Edge(
                    cost=final_cost,
                    metadata={
                        "edge_type": "osm_way",
                        "way_id": way.id,
                        "distance_m": distance_m,
                        "duration_s": duration_s,
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
        if node_id not in self.data_source.nodes:
            return None

        node = self.data_source.nodes[node_id]
        node_data: dict[str, GraphserverDataType] = {
            "osm_node_id": node.id,
            **node.tags,
        }
        # Create vertex with identity hash
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
        """Get estimated number of walkable edges in the provider.

        Note: This is calculated dynamically and may be approximate.
        """
        # Estimate: each way typically creates 2 edges per segment (bidirectional)
        # and ways have on average 3-4 nodes, so ~6-8 edges per way
        estimated_edges = 0
        for way in self.data_source.ways.values():
            segments = len(way.node_refs) - 1
            if segments > 0:
                # Check if oneway
                oneway = way.tags.get("oneway", "no")
                if oneway in {"yes", "true", "1"}:
                    estimated_edges += segments  # Only forward edges
                else:
                    estimated_edges += segments * 2  # Bidirectional
        return estimated_edges
