"""Utility functions for OSM providers."""

from __future__ import annotations

from graphserver.core import GraphserverDataType, Vertex


def create_osm_node_vertex(
    node_id: int,
    *,
    time: int | None = None,
) -> Vertex:
    """Create a standard OSM node vertex.

    Args:
        node_id: OSM node identifier
        time: Optional time value to include in the vertex

    Returns:
        Vertex instance with a stable identity hash based on the node ID
    """
    vertex_data: dict[str, GraphserverDataType] = {"osm_node_id": node_id}
    if time is not None:
        vertex_data["time"] = time

    identity_hash = hash(f"osm:{node_id}") & 0xFFFFFFFFFFFFFFFF
    return Vertex(vertex_data, hash_value=identity_hash)
