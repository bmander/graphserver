"""HTTP server for the route planner application."""

import logging
import math
import mimetypes
import os
import sys
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import routing_utils, web_utils

# Configure logging
logger = logging.getLogger(__name__)

# Graphserver imports for routing
try:
    from graphserver import Engine
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


class RoutePlannerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for route planner."""

    # Dependencies will be set by the server before serving requests
    # These replace the previous pattern of setting them on the class
    engine: "Engine | None" = None
    providers: dict[str, Any] = {}
    osm_data: "OSMDataSource | None" = None
    server_config: dict[str, Any] = {}

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests using route dispatch."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Route dispatch map for GET requests
        route_handlers = {
            "/": lambda: self.serve_file("static/index.html", "text/html"),
            "/api/status": self._handle_status,
            "/api/bounds": self._handle_bounds,
            "/api/providers": self._handle_providers,
        }

        # Check exact route matches first
        if path in route_handlers:
            route_handlers[path]()
        # Handle static files prefix
        elif path.startswith("/static/"):
            file_path = path[1:]  # Remove leading slash
            self.serve_file(file_path)
        else:
            self.send_error(404, "Not found")

    def do_POST(self) -> None:  # noqa: N802
        """Handle POST requests using route dispatch."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        # Route dispatch map for POST requests
        route_handlers = {
            "/api/route": self._handle_route_request,
        }

        # Check exact route matches
        if path in route_handlers:
            route_handlers[path]()
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

            if not full_path.is_relative_to(base_dir):
                self.send_error(403, "Forbidden: Path outside base directory")
                return
        except (OSError, ValueError):
            self.send_error(400, "Bad request: Invalid path")
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

    def _handle_status(self) -> None:
        """Handle GET /api/status - return server status and configuration."""
        web_utils.send_json_response(
            self,
            {
                "status": "ok",
                "message": "Route planner is running",
                "config": self.server_config,
            },
        )

    def _handle_bounds(self) -> None:
        """Handle GET /api/bounds - return OSM file bounds."""
        web_utils.send_json_response(self, self._get_osm_bounds())

    def _handle_providers(self) -> None:
        """Handle GET /api/providers - return provider information."""
        web_utils.send_json_response(self, self._get_providers_info())

    def log_message(self, fmt: str, *args: Any) -> None:
        """Custom log format."""
        print(f"[{self.address_string()}] {fmt % args}")

    def _get_osm_bounds(self) -> dict[str, float]:
        """Get OSM file bounds for map initialization."""
        # Use cached bounds from OSMDataSource for O(1) lookup
        osm_data = self.osm_data
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
        providers = self.providers

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
            "routing_available": self.engine is not None,
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
            engine = self.engine
            if not engine:
                web_utils.send_json_error(
                    self,
                    500,
                    "Routing engine not available",
                    error_details="Graphserver engine not initialized or routing data not loaded",
                )
                return

            # Perform routing
            self._perform_routing(engine, origin, destination)

        except Exception as e:
            logger.exception("Route request handling error")
            self.send_error(500, f"Internal server error: {e}")

    def _calculate_approx_distance_km(
        self, origin: dict[str, float], destination: dict[str, float]
    ) -> float:
        """Calculate approximate distance between two points in kilometers.

        Args:
            origin: Origin coordinates with lat/lng
            destination: Destination coordinates with lat/lng

        Returns:
            Approximate distance in kilometers (using simple Euclidean formula)
        """
        lat_diff = abs(destination["lat"] - origin["lat"])
        lng_diff = abs(destination["lng"] - origin["lng"])
        return math.sqrt(lat_diff**2 + lng_diff**2) * 111  # Rough conversion

    def _validate_and_parse_request(self) -> dict[str, Any] | None:
        """Validate and parse route request. Returns None if there's an error."""
        # Parse JSON body
        request_data = web_utils.parse_json_body(self)
        if request_data is None:
            return None

        # Validate required fields
        required_fields = ["origin", "destination"]
        missing_fields = web_utils.validate_request_fields(
            request_data, required_fields
        )
        if missing_fields:
            web_utils.send_http_error(
                self, 400, f"Missing required field: {missing_fields[0]}"
            )
            return None

        # Validate coordinates
        for point_name in ["origin", "destination"]:
            point = request_data[point_name]
            validated_point = web_utils.validate_point(point, point_name)
            if validated_point is None:
                web_utils.send_http_error(
                    self, 400, f"Invalid {point_name} coordinates"
                )
                return None
            # Update the request data with normalized coordinates
            request_data[point_name] = validated_point

        return request_data

    def _perform_routing(
        self, engine: "Engine", origin: dict[str, float], destination: dict[str, float]
    ) -> None:
        """Perform the actual routing calculation."""
        try:
            start_vertex = routing_utils.create_vertex_from_coordinates(
                origin["lat"], origin["lng"]
            )
            goal_vertex = routing_utils.create_vertex_from_coordinates(
                destination["lat"], destination["lng"]
            )

            # Get access provider
            providers = self.providers
            access_provider = providers.get("osm_access")

            if not access_provider:
                web_utils.send_json_error(
                    self,
                    500,
                    "OSM access provider not available",
                    error_code="PROVIDER_UNAVAILABLE",
                    error_details="The routing engine could not access OSM network data. This may indicate a configuration issue.",
                    debug_info={"providers_available": list(providers.keys())},
                )
                return

            # Calculate distance between points for diagnostics
            approx_distance_km = self._calculate_approx_distance_km(origin, destination)

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
                    web_utils.send_json_error(
                        self,
                        404,
                        "No route could be calculated between the selected points",
                        error_code="NO_ROUTE_FOUND",
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
                web_utils.send_json_error(
                    self,
                    500,
                    "Route calculation failed due to an internal error",
                    error_code="ROUTING_ENGINE_ERROR",
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
            osm_data = self.osm_data
            geometry_start_time = time.perf_counter()
            geojson_result = routing_utils.path_result_to_geojson(
                path_result, origin, destination, osm_data, debug_metrics=True
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

            web_utils.send_json_response(self, geojson_result)

        except Exception as e:
            logger.exception("Route calculation error")
            web_utils.send_json_error(
                self,
                500,
                "An unexpected error occurred during route calculation",
                error_code="UNKNOWN_ERROR",
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

            web_utils.send_json_error(
                self,
                400,
                "No roads found near the selected coordinates",
                error_code="NO_NEARBY_ROADS",
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
            web_utils.send_json_error(
                self,
                400,
                "Failed to connect coordinates to the road network",
                error_code="COORDINATE_LINKING_FAILED",
                error_details=f"Coordinate linking error: {error_msg}",
                debug_info={
                    "search_radius_m": search_radius,
                    "origin": origin,
                    "destination": destination,
                    "approximate_distance_km": round(approx_distance_km, 2),
                    "raw_error": error_msg,
                },
            )


def create_progress_callback() -> Callable[[str], None]:
    """Create a progress callback that displays updates on the same line.

    Returns:
        Callback function that displays progress with same-line updates
    """

    def progress_callback(msg: str) -> None:
        """Display progress message on the same line, clearing previous content.

        Args:
            msg: Progress message to display
        """
        # Clear the line by moving cursor to beginning and padding with spaces
        # Get terminal width or use reasonable default
        try:
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

        # Store dependencies on the handler class for access during requests
        # This replaces the previous pattern of using getattr()
        RoutePlannerHandler.server_config = {
            "osm_file": osm_file,
            "gtfs_files": self.gtfs_files,
            "routing_available": self.engine is not None,
            "provider_count": len(self.providers),
            "caching_enabled": self.enable_caching,
            "precaching_enabled": self.enable_precaching,
        }
        RoutePlannerHandler.engine = self.engine
        RoutePlannerHandler.providers = self.providers
        RoutePlannerHandler.osm_data = getattr(self, "osm_data", None)

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
