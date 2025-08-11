"""Routing utility functions for the route planner application."""

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import graphserver
    from graphserver import Vertex
    from graphserver.providers.osm import OSMDataSource

logger = logging.getLogger(__name__)


def create_vertex_from_coordinates(lat: float, lng: float) -> "Vertex":
    """Create a Vertex object from latitude/longitude coordinates."""
    try:
        from graphserver import Vertex

        return Vertex({"lat": lat, "lng": lng, "type": "coordinate"})
    except ImportError as e:
        # Handle case where graphserver is not available
        msg = "Graphserver is required for vertex creation"
        raise ImportError(msg) from e


def encode_polyline(coordinates: list[list[float]]) -> str:
    """Encode a list of [lng, lat] coordinates as a polyline string.

    Uses Google's polyline encoding algorithm to compress coordinate data.

    Args:
        coordinates: List of [longitude, latitude] pairs

    Returns:
        Encoded polyline string
    """
    if not coordinates:
        return ""

    # Constants for polyline encoding
    chunk_size = 0x20
    chunk_mask = 0x1F
    ascii_offset = 63

    def encode_value(value: int) -> str:
        """Encode a single coordinate value using variable-length encoding."""
        # Left shift and apply two's complement for negative values
        value = ~(value << 1) if value < 0 else (value << 1)

        encoded = ""
        while value >= chunk_size:
            encoded += chr((chunk_size | (value & chunk_mask)) + ascii_offset)
            value >>= 5
        encoded += chr(value + ascii_offset)
        return encoded

    polyline = ""
    prev_lat = 0
    prev_lng = 0

    for lng, lat in coordinates:
        # Convert to integers (multiply by 1e5 for precision)
        lat_int = int(round(lat * 1e5))
        lng_int = int(round(lng * 1e5))

        # Calculate deltas from previous point
        delta_lat = lat_int - prev_lat
        delta_lng = lng_int - prev_lng

        # Encode deltas
        polyline += encode_value(delta_lat)
        polyline += encode_value(delta_lng)

        # Update previous values
        prev_lat = lat_int
        prev_lng = lng_int

    return polyline


def extract_way_segment_coordinates(
    osm_data: "OSMDataSource",
    way_id: int,
    from_node_id: int,
    to_node_id: int,
    from_node_index: int | None = None,
    to_node_index: int | None = None,
) -> list[list[float]]:
    """Extract coordinates for a segment of an OSM way.

    Args:
        osm_data: OSM data source containing ways and nodes
        way_id: ID of the OSM way
        from_node_id: Starting node ID for the segment
        to_node_id: Ending node ID for the segment
        from_node_index: Index of from_node_id in the way (required)
        to_node_index: Index of to_node_id in the way (required)

    Returns:
        List of [lng, lat] coordinate pairs for the segment (excluding the first point)
    """
    if not osm_data or way_id not in osm_data.ways:
        return []

    if from_node_index is None or to_node_index is None:
        return []  # Indices are required for reliable operation

    way = osm_data.ways[way_id]
    node_refs = way.node_refs

    # Validate that the provided indices match the expected nodes
    if (
        from_node_index >= len(node_refs)
        or to_node_index >= len(node_refs)
        or node_refs[from_node_index] != from_node_id
        or node_refs[to_node_index] != to_node_id
    ):
        return []  # Invalid indices

    # Extract the segment based on the relationship between indices
    if from_node_index < to_node_index:
        # Forward direction: exclude from_node, include to_node
        segment_nodes = node_refs[from_node_index + 1 : to_node_index + 1]
    elif from_node_index > to_node_index:
        # Reverse direction: reverse the segment
        segment_nodes = node_refs[to_node_index:from_node_index][::-1]
    else:
        # Same node - empty segment
        segment_nodes = []

    # Convert node IDs to coordinates
    coordinates = []
    for node_id in segment_nodes:
        if node_id in osm_data.nodes:
            node = osm_data.nodes[node_id]
            coordinates.append([node.lon, node.lat])  # GeoJSON format: [lng, lat]

    return coordinates


def path_result_to_geojson(
    path_result: "graphserver.PathResult",
    origin: dict[str, float],
    destination: dict[str, float],
    osm_data: "OSMDataSource | None" = None,
    *,
    debug_metrics: bool = False,
) -> dict[str, Any]:
    """Convert a PathResult to GeoJSON format.

    Args:
        path_result: The pathfinding result from graphserver
        origin: Origin coordinates {"lat": float, "lng": float}
        destination: Destination coordinates {"lat": float, "lng": float}
        osm_data: OSM data source for geometry extraction
        debug_metrics: Whether to compute bandwidth savings and timing metrics

    Returns:
        GeoJSON FeatureCollection with route geometry and metadata
    """
    if not path_result or len(path_result) == 0:
        return {
            "type": "FeatureCollection",
            "features": [],
            "properties": {"total_cost": 0, "total_distance": 0, "status": "no_route"},
        }

    # Extract coordinates from path - now with actual OSM way geometry
    coordinates = [[origin["lng"], origin["lat"]]]
    total_cost = 0.0
    total_distance = 0.0
    previous_node_id = None

    # Remove unused enumerate and process path edges directly
    for path_edge in path_result:
        # Get target vertex and edge information
        target = path_edge.target
        edge = path_edge.edge

        # Cache metadata once to avoid duplicate hasattr checks
        edge_metadata = getattr(edge, "metadata", None)

        # Add to total cost
        if hasattr(edge, "cost"):
            cost = edge.cost
            if isinstance(cost, int | float):
                total_cost += cost

        # Add to total distance using actual OSM distance metadata
        if edge_metadata:
            distance_m = edge_metadata.get("distance_m", 0)
            if isinstance(distance_m, int | float):
                total_distance += distance_m

        # Try to extract actual way geometry if we have OSM data
        if osm_data and "osm_node_id" in target and previous_node_id:
            current_node_id = target["osm_node_id"]

            # Get way_id from cached metadata
            way_id = None
            if edge_metadata:
                way_id = edge_metadata.get("way_id")

            if way_id and previous_node_id and current_node_id and edge_metadata:
                # Get node indices from edge metadata if available
                from_node_index = edge_metadata.get("from_node_index")
                to_node_index = edge_metadata.get("to_node_index")

                # Extract the way segment coordinates
                segment_coords = extract_way_segment_coordinates(
                    osm_data,
                    way_id,
                    previous_node_id,
                    current_node_id,
                    from_node_index,
                    to_node_index,
                )
                coordinates.extend(segment_coords)
            elif "lat" in target and "lng" in target:
                # Fallback to direct coordinates if we can't get way geometry
                coordinates.append([target["lng"], target["lat"]])
        elif "lat" in target and "lng" in target:
            # Direct coordinate target (access edge to destination)
            coordinates.append([target["lng"], target["lat"]])

        # Update previous node for next iteration
        if "osm_node_id" in target:
            previous_node_id = target["osm_node_id"]

    # Add destination
    coordinates.append([destination["lng"], destination["lat"]])

    # Encode polyline for efficient transmission
    polyline_start_time = time.perf_counter() if debug_metrics else 0
    encoded_polyline = encode_polyline(coordinates)
    polyline_end_time = time.perf_counter() if debug_metrics else 0
    polyline_encoding_time_ms = (
        (polyline_end_time - polyline_start_time) * 1000 if debug_metrics else 0
    )

    # Create the route LineString feature with optimized geometry
    # Only include encoded polyline to minimize response size
    route_feature = {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": [],
        },  # Empty to save bandwidth
        "properties": {
            "route_type": "calculated_route",
            "encoded_polyline": encoded_polyline,
        },
    }

    # Base properties
    properties = {
        "total_cost": total_cost,
        "total_distance": total_distance,  # Actual distance from OSM edge metadata
        "status": "success",
    }

    # Only compute and include metrics when debug_metrics is enabled
    if debug_metrics:
        # Calculate encoded polyline size for metrics
        encoded_polyline_size = len(encoded_polyline.encode("utf-8"))

        # Add debug metrics to properties
        properties.update(
            {
                "polyline_encoding_time_ms": round(polyline_encoding_time_ms, 2),
                "encoded_polyline_size_bytes": encoded_polyline_size,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": [route_feature],
        "properties": properties,
    }
