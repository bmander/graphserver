"""OSM Network Provider

This module provides the OSMNetworkProvider class for navigation between
OSM nodes via the street/path network.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

from graphserver.core import Edge, Vertex, VertexEdgePair

from .parser import OSMParser
from .types import WalkingProfile

logger = logging.getLogger(__name__)


class OSMNetworkProvider:
    """OSM network provider for navigation between OSM nodes.

    This provider handles movement between OSM nodes via the actual street/path
    network. It only accepts vertices with OSM node IDs and returns edges to
    connected nodes based on the walkable OSM ways.
    """

    def __init__(
        self,
        osm_file: str | Path | None = None,
        *,
        parser: OSMParser | None = None,
        walking_profile: WalkingProfile | None = None,
    ) -> None:
        """Initialize OSM network provider.

        Args:
            osm_file: Path to OSM XML or PBF file (if parser not provided)
            parser: Pre-initialized OSM parser (if osm_file not provided)
            walking_profile: Configuration for pedestrian routing preferences

        Raises:
            ValueError: If neither osm_file nor parser is provided
            FileNotFoundError: If OSM file doesn't exist
            RuntimeError: If parsing fails
        """
        if parser is not None:
            self.parser = parser
        elif osm_file is not None:
            self.walking_profile = walking_profile or WalkingProfile()
            logger.info("Initializing OSM network provider from %s", osm_file)
            self.parser = OSMParser(self.walking_profile)
            self.parser.parse_file(osm_file)
        else:
            msg = "Either osm_file or parser must be provided"
            raise ValueError(msg)

        logger.info(
            "OSM network provider ready: %d nodes, %d edges",
            len(self.parser.nodes),
            len(self.parser.edges),
        )

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
            # Round coordinates to ~1 meter precision for matching tolerance
            rounded_lat = round(vertex_data["lat"], 5)
            rounded_lon = round(vertex_data["lon"], 5)
            hash_string = f"coord:{rounded_lat},{rounded_lon}"
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
            target_data = {
                "osm_node_id": target_node.id,
                "lat": target_node.lat,
                "lon": target_node.lon,
                **target_node.tags,
            }
            # Create target vertex with identity hash
            identity_hash = self._get_identity_hash(target_data)
            target_vertex = Vertex(target_data, hash_value=identity_hash)

            # Apply walking profile to get final cost
            way = self.parser.ways[osm_edge.way_id]
            walking_profile = (
                getattr(self, "walking_profile", None) or self.parser.walking_profile
            )
            final_cost = walking_profile.get_edge_cost(osm_edge, way)

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
        node_data = {
            "osm_node_id": node.id,
            "lat": node.lat,
            "lon": node.lon,
            **node.tags,
        }
        # Create vertex with identity hash
        identity_hash = self._get_identity_hash(node_data)
        return Vertex(node_data, hash_value=identity_hash)

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
