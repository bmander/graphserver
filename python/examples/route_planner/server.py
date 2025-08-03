"""HTTP server for the route planner application."""

import json
import mimetypes
import os
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse


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
        return {
            "south": 47.6,
            "west": -122.4,
            "north": 47.7,
            "east": -122.2
        }


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
        bounds_elem = root.find('bounds')
        if bounds_elem is not None:
            return {
                "south": float(bounds_elem.get('minlat')),
                "west": float(bounds_elem.get('minlon')),
                "north": float(bounds_elem.get('maxlat')),
                "east": float(bounds_elem.get('maxlon'))
            }
        
        # Method 2: Calculate bounds from all nodes
        lats, lons = [], []
        for node in root.findall('.//node'):
            lat = node.get('lat')
            lon = node.get('lon')
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
                "east": max(lons) + lon_buffer
            }
        
    except Exception as e:
        print(f"Warning: Failed to parse OSM bounds: {e}")
    
    # Default bounds (Seattle area) if all else fails
    return {
        "south": 47.6,
        "west": -122.4,
        "north": 47.7,
        "east": -122.2
    }


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

        # Store config for handlers to access
        RoutePlannerHandler.server_config = {
            "osm_file": osm_file,
            "gtfs_files": self.gtfs_files,
        }

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
