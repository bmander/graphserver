"""HTTP server for the route planner application."""

import json
import mimetypes
import os
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
