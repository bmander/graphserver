"""HTTP server for the route planner application."""

import json
import mimetypes
import os
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

# Graphserver imports for routing
try:
    import graphserver
    from graphserver import Engine, Vertex
    from graphserver.providers.osm import (
        OSMDataSource,
        OSMNetworkProvider,
        OSMAccessProvider,
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


def path_result_to_geojson(
    path_result: "graphserver.PathResult", origin: dict, destination: dict
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

    # Extract coordinates from path
    coordinates = [[origin["lng"], origin["lat"]]]
    total_cost = 0
    waypoints = []

    for i, path_edge in enumerate(path_result):
        # Get target vertex coordinates
        target = path_edge.target
        if "lat" in target and "lng" in target:
            coordinates.append([target["lng"], target["lat"]])

        # Add to total cost
        if hasattr(path_edge.edge, "cost"):
            cost = path_edge.edge.cost
            if isinstance(cost, (int, float)):
                total_cost += float(cost)

        # Create waypoint information
        waypoint = {
            "position": [target.get("lng", 0), target.get("lat", 0)],
            "instruction": f"Continue to waypoint {i + 1}",
            "cost": float(cost) if isinstance(cost, (int, float)) else 0,
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

    def do_GET(self) -> None:
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

    def do_POST(self) -> None:
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
        except (OSError, IOError) as e:
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

    def log_message(self, format: str, *args) -> None:
        """Custom log format."""
        print(f"[{self.address_string()}] {format % args}")

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
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length == 0:
                self.send_error(400, "Empty request body")
                return

            post_data = self.rfile.read(content_length)
            try:
                request_data = json.loads(post_data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.send_error(400, f"Invalid JSON: {e}")
                return

            # Validate request data
            required_fields = ["origin", "destination"]
            for field in required_fields:
                if field not in request_data:
                    self.send_error(400, f"Missing required field: {field}")
                    return

            origin = request_data["origin"]
            destination = request_data["destination"]

            # Validate coordinates
            for point_name, point in [("origin", origin), ("destination", destination)]:
                if (
                    not isinstance(point, dict)
                    or "lat" not in point
                    or "lng" not in point
                ):
                    self.send_error(400, f"Invalid {point_name} coordinates")
                    return
                try:
                    float(point["lat"])
                    float(point["lng"])
                except (ValueError, TypeError):
                    self.send_error(400, f"Invalid {point_name} coordinate values")
                    return

            # Get engine from class attribute
            engine = getattr(self.__class__, "engine", None)

            if not engine:
                self.send_json_response(
                    {
                        "error": "Routing engine not available",
                        "message": "Graphserver engine not initialized or routing data not loaded",
                    }
                )
                return

            # Calculate route
            try:
                start_vertex = create_vertex_from_coordinates(
                    origin["lat"], origin["lng"]
                )
                goal_vertex = create_vertex_from_coordinates(
                    destination["lat"], destination["lng"]
                )

                # Link coordinate vertices to nearest OSM nodes via access provider
                providers = getattr(self.__class__, "providers", {})
                access_provider = providers.get("osm_access")

                if not access_provider:
                    self.send_json_response(
                        {
                            "type": "FeatureCollection",
                            "features": [],
                            "properties": {
                                "status": "error",
                                "error": "OSM access provider not available",
                                "total_cost": 0,
                            },
                        }
                    )
                    return

                # Link start and goal vertices to OSM network
                try:
                    access_provider.link(start_vertex, origin["lat"], origin["lng"])
                    access_provider.link(
                        goal_vertex, destination["lat"], destination["lng"]
                    )
                except ValueError as e:
                    # Handle case where coordinates are too far from road network
                    error_msg = str(e)
                    if "No OSM node found" in error_msg:
                        self.send_json_response(
                            {
                                "type": "FeatureCollection",
                                "features": [],
                                "properties": {
                                    "status": "error",
                                    "error": "No roads found near the specified coordinates",
                                    "message": f"Try clicking closer to streets or roads. Search radius: {access_provider.search_radius_m}m",
                                    "total_cost": 0,
                                },
                            }
                        )
                    else:
                        self.send_json_response(
                            {
                                "type": "FeatureCollection",
                                "features": [],
                                "properties": {
                                    "status": "error",
                                    "error": f"Coordinate linking failed: {error_msg}",
                                    "total_cost": 0,
                                },
                            }
                        )
                    return

                # Now perform the route planning
                path_result = engine.plan(
                    start=start_vertex, goal=goal_vertex, planner="dijkstra"
                )

                # Convert to GeoJSON
                geojson_result = path_result_to_geojson(
                    path_result, origin, destination
                )

                # Add additional metadata
                geojson_result["request"] = {
                    "origin": origin,
                    "destination": destination,
                    "algorithm": "dijkstra",
                }

                self.send_json_response(geojson_result)

            except Exception as e:
                print(f"Route calculation error: {e}")
                self.send_json_response(
                    {
                        "type": "FeatureCollection",
                        "features": [],
                        "properties": {
                            "status": "error",
                            "error": str(e),
                            "total_cost": 0,
                        },
                    }
                )

        except Exception as e:
            print(f"Route request handling error: {e}")
            self.send_error(500, f"Internal server error: {e}")


def parse_osm_bounds(osm_file_path: str) -> dict:
    """Parse OSM file to extract geographic bounds.

    Args:
        osm_file_path: Path to the OSM file

    Returns:
        Dict with south, west, north, east bounds
    """
    try:
        tree = ET.parse(osm_file_path)
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
    ) -> None:
        """Initialize the route planner server.

        Args:
            host: Host to bind to
            port: Port to listen on
            osm_file: Path to OSM file
            gtfs_files: List of paths to GTFS files
        """
        self.host = host
        self.port = port
        self.osm_file = osm_file
        self.gtfs_files = gtfs_files or []

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
        }

        # Store non-serializable objects separately for route calculation
        RoutePlannerHandler.engine = self.engine
        RoutePlannerHandler.providers = self.providers

    def _init_routing_engine(self) -> None:
        """Initialize the graphserver engine and load providers."""
        if not GRAPHSERVER_AVAILABLE:
            print(
                "⚠️  Warning: Graphserver not available - routing functionality disabled"
            )
            return

        try:
            # Initialize the graphserver engine with edge caching
            print("🚀 Initializing graphserver engine...")
            self.engine = Engine(enable_edge_caching=True)

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
                raise OSError(f"Port {self.port} is already in use") from e
            raise

        print("🚀 Route Planner Server starting...")
        print(f"📍 Server: http://{self.host}:{self.port}")
        print(f"🗺️  OSM file: {self.osm_file}")

        if self.gtfs_files:
            print(f"🚌 GTFS files: {', '.join(self.gtfs_files)}")

        print(
            "\n✅ Server ready! Open http://localhost:{} in your browser".format(
                self.port
            )
        )
        print("Press Ctrl+C to stop\n")

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down server...")
        finally:
            httpd.server_close()
