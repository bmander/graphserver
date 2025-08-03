"""HTTP server for the route planner application."""

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

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




def extract_way_segment_coordinates(
    osm_data, way_id: int, from_node_id: int, to_node_id: int
) -> list[list[float]]:
    """Extract coordinates for a segment of an OSM way.

    Args:
        osm_data: OSM data source containing ways and nodes
        way_id: ID of the OSM way
        from_node_id: Starting node ID for the segment
        to_node_id: Ending node ID for the segment

    Returns:
        List of [lng, lat] coordinate pairs for the segment (excluding the first point)
    """
    if not osm_data:
        return []
        
    if way_id not in osm_data.ways:
        return []

    way = osm_data.ways[way_id]
    node_refs = way.node_refs

    try:
        # Find the indices of the from and to nodes
        from_index = node_refs.index(from_node_id)
        to_index = node_refs.index(to_node_id)
    except ValueError:
        # One of the nodes isn't in this way
        return []

    # Determine direction and extract the segment
    if from_index < to_index:
        # Forward direction
        segment_nodes = node_refs[
            from_index + 1 : to_index + 1
        ]  # Exclude from_node, include to_node
    else:
        # Reverse direction
        segment_nodes = node_refs[to_index:from_index][::-1]  # Reverse the segment

    # Convert node IDs to coordinates
    coordinates = []
    for node_id in segment_nodes:
        if node_id in osm_data.nodes:
            node = osm_data.nodes[node_id]
            coordinates.append([node.lon, node.lat])  # GeoJSON format: [lng, lat]

    return coordinates


def path_result_to_geojson(
    path_result: "graphserver.PathResult",
    origin: dict,
    destination: dict,
    osm_data=None,
) -> dict:
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
    total_cost = 0
    waypoints = []
    previous_node_id = None

    for i, path_edge in enumerate(path_result):
        # Get target vertex and edge information
        target = path_edge.target
        edge = path_edge.edge


        # Add to total cost
        if hasattr(edge, "cost"):
            cost = edge.cost
            if isinstance(cost, int | float):
                total_cost += float(cost)

        # Try to extract actual way geometry if we have OSM data
        if osm_data and "osm_node_id" in target and previous_node_id:
            current_node_id = target["osm_node_id"]
            
            # Get way_id from metadata
            way_id = None
            if hasattr(edge, "metadata") and edge.metadata:
                way_id = edge.metadata.get("way_id")
    
            if way_id and previous_node_id and current_node_id:
                # Extract the way segment coordinates
                segment_coords = extract_way_segment_coordinates(
                    osm_data, way_id, previous_node_id, current_node_id
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

        # Create waypoint information
        waypoint = {
            "position": [target.get("lng", 0), target.get("lat", 0)],
            "instruction": f"Continue to waypoint {i + 1}",
            "cost": float(cost) if isinstance(cost, int | float) else 0,
        }
        waypoints.append(waypoint)

    # Add destination
    coordinates.append([destination["lng"], destination["lat"]])

    # Create the route LineString feature
    route_feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coordinates},
        "properties": {"route_type": "calculated_route", "waypoints": waypoints},
    }

    return {
        "type": "FeatureCollection",
        "features": [route_feature],
        "properties": {
            "total_cost": total_cost,
            "total_distance": len(coordinates) * 100,  # Rough estimate
            "status": "success",
            "waypoint_count": len(waypoints),
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

    def send_json_response(self, data: dict) -> None:
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

    def log_message(self, fmt: str, *args) -> None:
        """Custom log format."""
        print(f"[{self.address_string()}] {fmt % args}")

    def _get_osm_bounds(self) -> dict:
        """Get OSM file bounds for map initialization."""
        server_config = getattr(self, "server_config", {})
        osm_file = server_config.get("osm_file")

        if not osm_file:
            return self._default_bounds()

        return parse_osm_bounds(osm_file)

    def _default_bounds(self) -> dict:
        """Return default bounds (Seattle area) if OSM parsing fails."""
        return {"south": 47.6, "west": -122.4, "north": 47.7, "east": -122.2}

    def _get_providers_info(self) -> dict:
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
            print(f"Route request handling error: {e}")
            self.send_error(500, f"Internal server error: {e}")

    def _validate_and_parse_request(self) -> dict | None:
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

        return request_data

    def _perform_routing(self, engine, origin: dict, destination: dict) -> None:
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

            # Perform route planning
            try:
                path_result = engine.plan(
                    start=start_vertex, goal=goal_vertex, planner="dijkstra"
                )

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
                        },
                    )
                    return

            except Exception as routing_error:
                self._send_error_response(
                    error_code="ROUTING_ENGINE_ERROR",
                    error_message="Route calculation failed due to an internal error",
                    error_details=f"The routing engine encountered an error: {str(routing_error)}",
                    debug_info={
                        "engine_error": str(routing_error),
                        "origin": origin,
                        "destination": destination,
                        "approximate_distance_km": round(approx_distance_km, 2),
                    },
                )
                return

            # Successfully found route
            osm_data = getattr(self.__class__, "osm_data", None)
            geojson_result = path_result_to_geojson(
                path_result, origin, destination, osm_data
            )
            geojson_result["request"] = {
                "origin": origin,
                "destination": destination,
                "algorithm": "dijkstra",
            }

            self.send_json_response(geojson_result)

        except Exception as e:
            print(f"Route calculation error: {e}")
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
        access_provider,
        origin: dict,
        destination: dict,
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
        debug_info: dict,
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



def parse_osm_bounds(osm_file_path: str) -> dict:
    """Parse OSM file to extract geographic bounds.

    Args:
        osm_file_path: Path to the OSM file

    Returns:
        Dict with south, west, north, east bounds
    """
    try:
        from defusedxml import ElementTree

        tree = ElementTree.parse(osm_file_path)
        root = tree.getroot()

        # Method 1: Try to find explicit bounds element
        bounds_elem = root.find("bounds")
        if bounds_elem is not None:
            return {
                "south": float(bounds_elem.get("minlat")),
                "west": float(bounds_elem.get("minlon")),
                "north": float(bounds_elem.get("maxlat")),
                "east": float(bounds_elem.get("maxlon")),
            }

        # Method 2: Calculate bounds from all nodes
        lats, lons = [], []
        for node in root.findall(".//node"):
            lat = node.get("lat")
            lon = node.get("lon")
            if lat is not None and lon is not None:
                lats.append(float(lat))
                lons.append(float(lon))

        if lats and lons:
            # Add a small buffer around the bounds
            lat_buffer = (max(lats) - min(lats)) * 0.1
            lon_buffer = (max(lons) - min(lons)) * 0.1

            return {
                "south": min(lats) - lat_buffer,
                "west": min(lons) - lon_buffer,
                "north": max(lats) + lat_buffer,
                "east": max(lons) + lon_buffer,
            }

    except Exception as e:
        print(f"Warning: Failed to parse OSM bounds: {e}")

    # Default bounds (Seattle area) if all else fails
    return {"south": 47.6, "west": -122.4, "north": 47.7, "east": -122.2}


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
    ) -> None:
        """Initialize the route planner server.

        Args:
            host: Host to bind to
            port: Port to listen on
            osm_file: Path to OSM file
            gtfs_files: List of paths to GTFS files
            enable_caching: Enable graph edge caching for better performance
        """
        self.host = host
        self.port = port
        self.osm_file = osm_file
        self.gtfs_files = gtfs_files or []
        self.enable_caching = enable_caching

        # Initialize graphserver engine and providers
        self.engine = None
        self.providers = {}
        self._init_routing_engine()

        # Store config for handlers to access (only JSON-serializable data)
        RoutePlannerHandler.server_config = {
            "osm_file": osm_file,
            "gtfs_files": self.gtfs_files,
            "routing_available": self.engine is not None,
            "provider_count": len(self.providers),
            "caching_enabled": self.enable_caching,
        }

        # Store non-serializable objects separately for route calculation
        RoutePlannerHandler.engine = self.engine
        RoutePlannerHandler.providers = self.providers
        RoutePlannerHandler.osm_data = getattr(self, "osm_data", None)

    def _init_routing_engine(self) -> None:
        """Initialize the graphserver engine and load providers."""
        if not GRAPHSERVER_AVAILABLE:
            print(
                "⚠️  Warning: Graphserver not available - routing functionality disabled"
            )
            return

        try:
            # Initialize the graphserver engine
            caching_status = "enabled" if self.enable_caching else "disabled"
            print(f"🚀 Initializing graphserver engine (caching {caching_status})...")
            self.engine = Engine(enable_edge_caching=self.enable_caching)

            # Load OSM providers if OSM file is provided
            if self.osm_file:
                self._load_osm_providers()

            # Load transit providers if GTFS files are provided
            if self.gtfs_files and TRANSIT_AVAILABLE:
                self._load_transit_providers()

            print(
                f"✅ Graphserver engine initialized with {len(self.providers)} providers"
            )

        except Exception as e:
            print(f"❌ Failed to initialize graphserver engine: {e}")
            self.engine = None
            self.providers = {}

    def _load_osm_providers(self) -> None:
        """Load and register OSM providers."""
        try:
            print(f"📍 Loading OSM data from {self.osm_file}...")

            # Initialize OSM data source
            osm_data = OSMDataSource(
                self.osm_file, progress_callback=lambda msg: print(f"  {msg}")
            )

            # Store OSM data source for geometry lookups
            self.osm_data = osm_data

            # Create and register OSM providers
            network_provider = OSMNetworkProvider(osm_data)
            access_provider = OSMAccessProvider(osm_data)

            self.engine.register_provider("osm_network", network_provider)
            self.engine.register_provider("osm_access", access_provider)

            self.providers["osm_network"] = network_provider
            self.providers["osm_access"] = access_provider

            print(
                f"✅ OSM providers loaded: {len(osm_data.nodes)} nodes, {len(osm_data.ways)} ways"
            )

        except Exception as e:
            print(f"❌ Failed to load OSM providers: {e}")
            raise

    def _load_transit_providers(self) -> None:
        """Load and register transit providers for GTFS files."""
        try:
            for gtfs_file in self.gtfs_files:
                print(f"🚌 Loading GTFS data from {gtfs_file}...")

                transit_provider = TransitProvider(
                    gtfs_file, progress_callback=lambda msg: print(f"  {msg}")
                )

                # Use filename as provider name
                provider_name = f"transit_{Path(gtfs_file).stem}"
                self.engine.register_provider(provider_name, transit_provider)
                self.providers[provider_name] = transit_provider

            print(f"✅ Transit providers loaded for {len(self.gtfs_files)} GTFS files")

        except Exception as e:
            print(f"❌ Failed to load transit providers: {e}")
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

        print(f"\n✅ Server ready! Open http://localhost:{self.port} in your browser")
        print("Press Ctrl+C to stop\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down server...")
        finally:
            httpd.server_close()
