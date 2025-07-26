"""HTTP request handlers for the graph web browser."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse, parse_qs

from .templates import generate_html_response


def parse_value(value_str: str) -> str | int | float:
    """Convert string to appropriate type (float, int, or str)."""
    try:
        # Try float first (handles decimals)
        if '.' in value_str:
            return float(value_str)
        # Try int if no decimal point
        return int(value_str)
    except ValueError:
        # Default to string
        return value_str


class GraphRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for graph browsing."""

    def __init__(self, *args, server_config: dict[str, Any] | None = None,
                 **kwargs):
        self.server_config = server_config or {}
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            # Parse the URL
            parsed_url = urlparse(self.path)

            if parsed_url.path != '/':
                self.send_error(404, "Only / endpoint is supported")
                return

            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            vertex_props: dict[str, str | int | float] = {}

            for key, values in query_params.items():
                # Take the first value for each parameter
                if values:
                    vertex_props[key] = parse_value(values[0])

            # Generate HTML response
            html_content = generate_html_response(vertex_props,
                                                  self.server_config)

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")

    def log_message(self, format: str, *args: Any) -> None:
        """Custom log message to show requests."""
        print(f"[{self.address_string()}] {format % args}")
