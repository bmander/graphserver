"""HTTP server for the route planner application."""

import json
import logging
import mimetypes
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger(__name__)

# Graphserver imports for routing
try:
    import graphserver
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import (
        OSMAccessProvider,
        OSMDataSource,
        OSMNetworkProvider,
    )

    try:
        from graphserver.providers.transit import TransitProvider

        TRANSIT_AVAILABLE = True
    except ImportError:
        TRANSIT_AVAILABLE = False
    GRAPHSERVER_AVAILABLE = True
except ImportError:
    GRAPHSERVER_AVAILABLE = False
    TRANSIT_AVAILABLE = False


def create_vertex_from_coordinates(lat: float, lng: float) -> "Vertex":
    """Create a Vertex object from latitude/longitude coordinates."""
    return Vertex({"lat": lat, "lng": lng, "type": "coordinate"})


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
    osm_data: OSMDataSource | None = None,
) -> dict[str, Any]:
    """Convert a PathResult to GeoJSON format.

    Args:
        path_result: The pathfinding result from graphserver
        origin: Origin coordinates {"lat": float, "lng": float}
        destination: Destination coordinates {"lat": float, "lng": float}

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

    for _, path_edge in enumerate(path_result):
        # Get target vertex and edge information
        target = path_edge.target
        edge = path_edge.edge

        # Add to total cost
        if hasattr(edge, "cost"):
            cost = edge.cost
            if isinstance(cost, int | float):
                total_cost += cost

        # Add to total distance using actual OSM distance metadata
        if hasattr(edge, "metadata") and edge.metadata:
            distance_m = edge.metadata.get("distance_m", 0)
            if isinstance(distance_m, int | float):
                total_distance += distance_m

        # Try to extract actual way geometry if we have OSM data
        if osm_data and "osm_node_id" in target and previous_node_id:
            current_node_id = target["osm_node_id"]

            # Get way_id from metadata
            way_id = None
            if hasattr(edge, "metadata") and edge.metadata:
                way_id = edge.metadata.get("way_id")

            if way_id and previous_node_id and current_node_id:
                # Get node indices from edge metadata if available
                from_node_index = edge.metadata.get("from_node_index")
                to_node_index = edge.metadata.get("to_node_index")

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

    # Encode polyline for efficient transmission with timing
    import json
    import time

    polyline_start_time = time.perf_counter()
    encoded_polyline = encode_polyline(coordinates)
    polyline_end_time = time.perf_counter()
    polyline_encoding_time_ms = (polyline_end_time - polyline_start_time) * 1000

    # Calculate bandwidth savings from optimizations
    # 1. Coordinates JSON vs encoded polyline
    original_coords_size = len(json.dumps(coordinates).encode("utf-8"))
    encoded_polyline_size = len(encoded_polyline.encode("utf-8"))

    # 2. Estimate waypoint data size that would have been sent
    # Each waypoint typically has position[2], instruction, cost = ~60-80 bytes per waypoint
    estimated_waypoint_count = len(path_result)
    estimated_waypoints_size = estimated_waypoint_count * 70  # Rough estimate

    # Total savings: coordinates + waypoints
    total_original_size = original_coords_size + estimated_waypoints_size
    total_optimized_size = encoded_polyline_size
    bandwidth_savings_bytes = total_original_size - total_optimized_size
    bandwidth_savings_percent = (
        (bandwidth_savings_bytes / total_original_size * 100)
        if total_original_size > 0
        else 0
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

    return {
        "type": "FeatureCollection",
        "features": [route_feature],
        "properties": {
            "total_cost": total_cost,
            "total_distance": total_distance,  # Actual distance from OSM edge metadata
            "status": "success",
            "coordinate_count": len(coordinates),
            "polyline_length": len(encoded_polyline),
            "polyline_encoding_time_ms": round(polyline_encoding_time_ms, 2),
            "original_coords_size_bytes": original_coords_size,
            "estimated_waypoints_size_bytes": estimated_waypoints_size,
            "total_original_size_bytes": total_original_size,
            "encoded_polyline_size_bytes": encoded_polyline_size,
            "bandwidth_savings_bytes": bandwidth_savings_bytes,
            "bandwidth_savings_percent": round(bandwidth_savings_percent, 1),
        },
    }


class RoutePlannerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for route planner."""

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Serve index.html for root
        if path == "/":
            self.serve_file("static/index.html", "text/html")
        # Serve static files
        elif path.startswith("/static/"):
            file_path = path[1:]  # Remove leading slash
            self.serve_file(file_path)
        # API endpoints
        elif path == "/api/status":
            self.send_json_response(
                {
                    "status": "ok",
                    "message": "Route planner is running",
                    "config": getattr(self, "server_config", {}),
                }
            )
        elif path == "/api/bounds":
            self.send_json_response(self._get_osm_bounds())
        elif path == "/api/providers":
            self.send_json_response(self._get_providers_info())
        else:
            self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == "/api/route":
            self._handle_route_request()
        else:
            self.send_error(404, "Not found")

    def serve_file(self, file_path: str, content_type: str | None = None) -> None:
        """Serve a static file."""
        # Get the directory where server.py is located
        base_dir = Path(__file__).parent
        full_path = base_dir / file_path

        # Security check: ensure path is within base directory
        try:
            full_path = full_path.resolve()
            base_dir = base_dir.resolve()
            if not str(full_path).startswith(str(base_dir)):
                self.send_error(403, "Forbidden")
                return
        except (OSError, ValueError):
            self.send_error(400, "Bad request")
            return

        if not full_path.exists() or not full_path.is_file():
            self.send_error(404, "File not found")
            return

        # Determine content type
        if content_type is None:
            content_type, _ = mimetypes.guess_type(str(full_path))
            if content_type is None:
                content_type = "application/octet-stream"

        try:
            # Send file
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()

            with open(full_path, "rb") as f:
                self.wfile.write(f.read())
        except OSError as e:
            self.send_error(500, f"Error reading file: {e}")

    def send_json_response(self, data: dict[str, Any]) -> None:
        """Send JSON response."""
        try:
            response_body = json.dumps(data, indent=2).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()

            self.wfile.write(response_body)
        except (TypeError, ValueError) as e:
            self.send_error(500, f"Error serializing JSON: {e}")

    def log_message(self, fmt: str, *args: Any) -> None:
        """Custom log format."""
        print(f"[{self.address_string()}] {fmt % args}")

    def _get_osm_bounds(self) -> dict[str, float]:
        """Get OSM file bounds for map initialization."""
        # Use cached bounds from OSMDataSource for O(1) lookup
        osm_data = getattr(self.__class__, "osm_data", None)
        if osm_data and hasattr(osm_data, "get_bounds"):
            bounds = osm_data.get_bounds()
            if isinstance(bounds, dict):
                return bounds

        # Fallback to default bounds if no OSM data available
        return self._default_bounds()

    def _default_bounds(self) -> dict[str, float]:
        """Return default bounds (Seattle area) if OSM parsing fails."""
        return {"south": 47.6, "west": -122.4, "north": 47.7, "east": -122.2}

    def _get_providers_info(self) -> dict[str, Any]:
        """Get information about loaded providers."""
        providers = getattr(self.__class__, "providers", {})

        provider_info = {}
        for name, provider in providers.items():
            info = {"name": name, "type": "unknown"}

            # Add specific information based on provider type
            if "osm" in name:
                info["type"] = "osm"
                if hasattr(provider, "data_source"):
                    osm_data = provider.data_source
                    info.update(
                        {
                            "node_count": len(osm_data.nodes)
                            if hasattr(osm_data, "nodes")
                            else 0,
                            "way_count": len(osm_data.ways)
                            if hasattr(osm_data, "ways")
                            else 0,
                        }
                    )
            elif "transit" in name:
                info["type"] = "transit"

            provider_info[name] = info

        return {
            "providers": provider_info,
            "total_count": len(providers),
            "routing_available": getattr(self.__class__, "engine", None) is not None,
        }

    def _handle_route_request(self) -> None:
        """Handle route calculation requests."""
        try:
            # Validate and parse request data
            request_data = self._validate_and_parse_request()
            if request_data is None:
                return

            origin = request_data["origin"]
            destination = request_data["destination"]

            # Check engine availability
            engine = getattr(self.__class__, "engine", None)
            if not engine:
                self.send_json_response(
                    {
                        "error": "Routing engine not available",
                        "message": "Graphserver engine not initialized or routing data not loaded",
                    }
                )
                return

            # Perform routing
            self._perform_routing(engine, origin, destination)

        except Exception as e:
            logger.exception("Route request handling error")
            self.send_error(500, f"Internal server error: {e}")

    def _validate_and_parse_request(self) -> dict[str, Any] | None:
        """Validate and parse route request. Returns None if there's an error."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            self.send_error(400, "Empty request body")
            return None

        try:
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            self.send_error(400, f"Invalid JSON: {e}")
            return None

        # Validate required fields
        required_fields = ["origin", "destination"]
        for field in required_fields:
            if field not in request_data:
                self.send_error(400, f"Missing required field: {field}")
                return None

        # Validate coordinates
        for point_name, point in [
            ("origin", request_data["origin"]),
            ("destination", request_data["destination"]),
        ]:
            if not isinstance(point, dict) or "lat" not in point or "lng" not in point:
                self.send_error(400, f"Invalid {point_name} coordinates")
                return None
            try:
                float(point["lat"])
                float(point["lng"])
            except (ValueError, TypeError):
                self.send_error(400, f"Invalid {point_name} coordinate values")
                return None

        return request_data  # type: ignore[no-any-return]

    def _perform_routing(
        self, engine: "Engine", origin: dict[str, float], destination: dict[str, float]
    ) -> None:
        """Perform the actual routing calculation."""
        try:
            start_vertex = create_vertex_from_coordinates(origin["lat"], origin["lng"])
            goal_vertex = create_vertex_from_coordinates(
                destination["lat"], destination["lng"]
            )

            # Get access provider
            providers = getattr(self.__class__, "providers", {})
            access_provider = providers.get("osm_access")

            if not access_provider:
                self._send_error_response(
                    error_code="PROVIDER_UNAVAILABLE",
                    error_message="OSM access provider not available",
                    error_details="The routing engine could not access OSM network data. This may indicate a configuration issue.",
                    debug_info={"providers_available": list(providers.keys())},
                )
                return

            # Calculate distance between points for diagnostics
            import math

            lat_diff = abs(destination["lat"] - origin["lat"])
            lng_diff = abs(destination["lng"] - origin["lng"])
            approx_distance_km = (
                math.sqrt(lat_diff**2 + lng_diff**2) * 111
            )  # Rough conversion

            # Link vertices to network
            try:
                access_provider.link(start_vertex, origin["lat"], origin["lng"])
                access_provider.link(
                    goal_vertex, destination["lat"], destination["lng"]
                )
            except ValueError as e:
                self._handle_linking_error(
                    e, access_provider, origin, destination, approx_distance_km
                )
                return

            # Perform route planning with timing
            routing_start_time = time.perf_counter()
            try:
                path_result = engine.plan(
                    start=start_vertex, goal=goal_vertex, planner="dijkstra"
                )
                routing_end_time = time.perf_counter()
                routing_time_ms = (routing_end_time - routing_start_time) * 1000

                # Check if route was found
                if not path_result or len(path_result) == 0:
                    self._send_error_response(
                        error_code="NO_ROUTE_FOUND",
                        error_message="No route could be calculated between the selected points",
                        error_details="The routing algorithm could not find a connected path between the origin and destination.",
                        debug_info={
                            "origin": origin,
                            "destination": destination,
                            "approximate_distance_km": round(approx_distance_km, 2),
                            "algorithm": "dijkstra",
                            "search_radius_m": getattr(
                                access_provider, "search_radius_m", None
                            ),
                            "routing_time_ms": round(routing_time_ms, 2),
                        },
                    )
                    return

            except Exception as routing_error:
                # Calculate partial timing if we have it
                routing_error_time_ms = (
                    time.perf_counter() - routing_start_time
                ) * 1000
                self._send_error_response(
                    error_code="ROUTING_ENGINE_ERROR",
                    error_message="Route calculation failed due to an internal error",
                    error_details=f"The routing engine encountered an error: {str(routing_error)}",
                    debug_info={
                        "engine_error": str(routing_error),
                        "origin": origin,
                        "destination": destination,
                        "approximate_distance_km": round(approx_distance_km, 2),
                        "routing_time_ms": round(routing_error_time_ms, 2),
                    },
                )
                return

            # Successfully found route - collect geometry with timing
            osm_data = getattr(self.__class__, "osm_data", None)
            geometry_start_time = time.perf_counter()
            geojson_result = path_result_to_geojson(
                path_result, origin, destination, osm_data
            )
            geometry_end_time = time.perf_counter()
            geometry_time_ms = (geometry_end_time - geometry_start_time) * 1000
            # Add timing statistics to the response
            geojson_result["request"] = {
                "origin": origin,
                "destination": destination,
                "algorithm": "dijkstra",
            }
            geojson_result["properties"]["timing"] = {
                "routing_time_ms": round(routing_time_ms, 2),
                "geometry_time_ms": round(geometry_time_ms, 2),
                "total_time_ms": round(routing_time_ms + geometry_time_ms, 2),
            }

            self.send_json_response(geojson_result)

        except Exception as e:
            logger.exception("Route calculation error")
            self._send_error_response(
                error_code="UNKNOWN_ERROR",
                error_message="An unexpected error occurred during route calculation",
                error_details=f"Internal server error: {str(e)}",
                debug_info={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                },
            )

    def _handle_linking_error(
        self,
        error: ValueError,
        access_provider: "OSMAccessProvider",
        origin: dict[str, float],
        destination: dict[str, float],
        approx_distance_km: float,
    ) -> None:
        """Handle coordinate linking errors with detailed diagnostics."""
        error_msg = str(error)
        search_radius = getattr(access_provider, "search_radius_m", "unknown")

        if "No OSM node found" in error_msg:
            # Determine which point failed by checking coordinates in error message
            failed_point = "unknown"
            if (
                f"{origin['lat']:.6f}" in error_msg
                or f"{origin['lng']:.6f}" in error_msg
            ):
                failed_point = "origin"
            elif (
                f"{destination['lat']:.6f}" in error_msg
                or f"{destination['lng']:.6f}" in error_msg
            ):
                failed_point = "destination"

            self._send_error_response(
                error_code="NO_NEARBY_ROADS",
                error_message="No roads found near the selected coordinates",
                error_details=f"Could not find any OSM road network within {search_radius}m of the {failed_point} point.",
                debug_info={
                    "failed_point": failed_point,
                    "search_radius_m": search_radius,
                    "origin": origin,
                    "destination": destination,
                    "approximate_distance_km": round(approx_distance_km, 2),
                    "raw_error": error_msg,
                },
            )
        else:
            self._send_error_response(
                error_code="COORDINATE_LINKING_FAILED",
                error_message="Failed to connect coordinates to the road network",
                error_details=f"Coordinate linking error: {error_msg}",
                debug_info={
                    "search_radius_m": search_radius,
                    "origin": origin,
                    "destination": destination,
                    "approximate_distance_km": round(approx_distance_km, 2),
                    "raw_error": error_msg,
                },
            )

    def _send_error_response(
        self,
        error_code: str,
        error_message: str,
        error_details: str,
        debug_info: dict[str, Any],
    ) -> None:
        """Send a structured error response with detailed information."""
        response = {
            "type": "FeatureCollection",
            "features": [],
            "properties": {
                "status": "error",
                "error": error_message,
                "error_code": error_code,
                "error_details": error_details,
                "debug_info": debug_info,
                "total_cost": 0,
            },
        }
        self.send_json_response(response)


def create_progress_callback() -> Callable[[str], None]:
    """Create a progress callback that displays updates on the same line.

    Returns:
        Callback function that displays progress with same-line updates
    """
    import sys

    def progress_callback(msg: str) -> None:
        """Display progress message on the same line, clearing previous content.

        Args:
            msg: Progress message to display
        """
        # Clear the line by moving cursor to beginning and padding with spaces
        # Get terminal width or use reasonable default
        try:
            import os

            terminal_width = os.get_terminal_size().columns
        except (AttributeError, OSError):
            terminal_width = 80

        # Format message with indentation
        formatted_msg = f"  {msg}"

        # Ensure message doesn't exceed terminal width
        if len(formatted_msg) >= terminal_width:
            formatted_msg = formatted_msg[: terminal_width - 4] + "..."

        # Clear line and print message without newline
        # Move to beginning of line, clear it, then print message
        sys.stdout.write(f"\r{' ' * (terminal_width - 1)}\r{formatted_msg}")
        sys.stdout.flush()

    return progress_callback


class RoutePlannerServer:
    """Main server class for route planner."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        osm_file: str | None = None,
        gtfs_files: list[str] | None = None,
        *,
        enable_caching: bool = False,
        enable_precaching: bool = False,
    ) -> None:
        """Initialize the route planner server.

        Args:
            host: Host to bind to
            port: Port to listen on
            osm_file: Path to OSM file
            gtfs_files: List of paths to GTFS files
            enable_caching: Enable graph edge caching for better performance
            enable_precaching: Pre-cache the entire OSM graph for maximum performance
        """
        self.host = host
        self.port = port
        self.osm_file = osm_file
        self.gtfs_files = gtfs_files or []
        self.enable_caching = enable_caching
        self.enable_precaching = enable_precaching

        # Initialize graphserver engine and providers
        self.engine: Engine | None = None
        self.providers: dict[str, Any] = {}
        self._init_routing_engine()

        # Store config for handlers to access (only JSON-serializable data)
        RoutePlannerHandler.server_config = {  # type: ignore[attr-defined]
            "osm_file": osm_file,
            "gtfs_files": self.gtfs_files,
            "routing_available": self.engine is not None,
            "provider_count": len(self.providers),
            "caching_enabled": self.enable_caching,
            "precaching_enabled": self.enable_precaching,
        }

        # Store non-serializable objects separately for route calculation
        RoutePlannerHandler.engine = self.engine  # type: ignore[attr-defined]
        RoutePlannerHandler.providers = self.providers  # type: ignore[attr-defined]
        RoutePlannerHandler.osm_data = getattr(self, "osm_data", None)  # type: ignore[attr-defined]

    def _init_routing_engine(self) -> None:
        """Initialize the graphserver engine and load providers."""
        if not GRAPHSERVER_AVAILABLE:
            logger.warning("Graphserver not available - routing functionality disabled")
            return

        try:
            # Initialize the graphserver engine
            caching_status = "enabled" if self.enable_caching else "disabled"
            logger.info("Initializing graphserver engine (caching %s)", caching_status)
            self.engine = Engine(enable_edge_caching=self.enable_caching)

            # Load OSM providers if OSM file is provided
            if self.osm_file is not None:
                self._load_osm_providers()

            # Load transit providers if GTFS files are provided
            if self.gtfs_files and TRANSIT_AVAILABLE:
                self._load_transit_providers()

            logger.info(
                "Graphserver engine initialized with %d providers", len(self.providers)
            )

        except Exception:
            logger.exception("Failed to initialize graphserver engine")
            self.engine = None
            self.providers = {}

    def _load_osm_providers(self) -> None:
        """Load and register OSM providers."""
        try:
            logger.info("Loading OSM data from %s", self.osm_file)

            # Initialize OSM data source with same-line progress updates
            progress_callback = create_progress_callback()
            osm_data = OSMDataSource(
                str(self.osm_file), progress_callback=progress_callback
            )

            # Print newline to complete progress line
            print()

            # Store OSM data source for geometry lookups
            self.osm_data = osm_data

            # Create and register OSM providers
            network_provider = OSMNetworkProvider(osm_data)
            access_provider = OSMAccessProvider(osm_data)

            if self.engine is not None:
                self.engine.register_provider("osm_network", network_provider)
                self.engine.register_provider("osm_access", access_provider)

            self.providers["osm_network"] = network_provider
            self.providers["osm_access"] = access_provider

            logger.info(
                "OSM providers loaded: %d nodes, %d ways",
                len(osm_data.nodes),
                len(osm_data.ways),
            )

            # Precache the entire OSM graph if requested
            if self.enable_precaching:
                self._precache_osm_graph(network_provider)

        except Exception:
            logger.exception("Failed to load OSM providers")
            raise

    def _precache_osm_graph(self, network_provider: "OSMNetworkProvider") -> None:
        """Pre-cache the entire OSM graph for maximum routing performance."""
        try:
            logger.info("Starting OSM graph precaching")

            # Get all seed vertices from the network provider
            logger.debug("Getting seed vertices from OSM network")
            seed_vertices = network_provider.seed_vertices()

            if not seed_vertices:
                logger.warning("No seed vertices found, skipping precaching")
                return

            vertex_count = len(seed_vertices)
            logger.info("Found %s seed vertices to precache", f"{vertex_count:,}")

            # Record start time for performance reporting
            import time

            start_time = time.time()

            # Pre-cache the subgraph from all seed vertices
            logger.info("Pre-caching OSM graph edges")
            if self.engine is not None:
                self.engine.precache_subgraph(
                    provider_name="osm_network",
                    seed_vertices=seed_vertices,
                    max_depth=0,  # No depth limit - cache everything
                    max_vertices=0,  # No vertex limit - cache everything
                )

            # Calculate and report completion
            end_time = time.time()
            duration = end_time - start_time

            logger.info("OSM graph precaching completed in %.2f seconds", duration)
            logger.info(
                "All %s vertices and their edges are now cached for maximum performance",
                f"{vertex_count:,}",
            )

        except Exception:
            logger.exception("Failed to precache OSM graph")
            # Don't raise - we can still operate without precaching
            logger.warning(
                "Continuing without precaching, routing will still work but may be slower"
            )

    def _load_transit_providers(self) -> None:
        """Load and register transit providers for GTFS files."""
        try:
            for gtfs_file in self.gtfs_files:
                logger.info("Loading GTFS data from %s", gtfs_file)

                progress_callback = create_progress_callback()
                transit_provider = TransitProvider(
                    gtfs_file, progress_callback=progress_callback
                )

                # Print newline to complete progress line
                print()

                # Use filename as provider name
                provider_name = f"transit_{Path(gtfs_file).stem}"
                if self.engine is not None:
                    self.engine.register_provider(provider_name, transit_provider)
                self.providers[provider_name] = transit_provider

            logger.info(
                "Transit providers loaded for %d GTFS files", len(self.gtfs_files)
            )

        except Exception:
            logger.exception("Failed to load transit providers")
            raise

    def run(self) -> None:
        """Start the HTTP server."""
        server_address = (self.host, self.port)

        try:
            httpd = HTTPServer(server_address, RoutePlannerHandler)
        except OSError as e:
            if "Address already in use" in str(e):
                msg = f"Port {self.port} is already in use"
                raise OSError(msg) from e
            raise

        print("🚀 Route Planner Server starting...")
        print(f"📍 Server: http://{self.host}:{self.port}")
        print(f"🗺️  OSM file: {self.osm_file}")

        if self.gtfs_files:
            print(f"🚌 GTFS files: {', '.join(self.gtfs_files)}")

        # Show caching status
        caching_status = "enabled" if self.enable_caching else "disabled"
        print(f"💾 Edge caching: {caching_status}")

        if self.enable_precaching:
            print("🚀 OSM graph precaching: enabled (maximum performance)")
        elif self.enable_caching:
            print("⚡ OSM graph precaching: disabled (edges cached on demand)")

        print(f"\n✅ Server ready! Open http://localhost:{self.port} in your browser")
        print("Press Ctrl+C to stop\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down server...")
        finally:
            httpd.server_close()
