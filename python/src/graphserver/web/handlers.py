"""HTTP request handlers for the graph web browser."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import parse_qs, urlparse

from graphserver import Vertex

from .templates import generate_html_response


def parse_value(value_str: str) -> str | int | float:
    """Convert string to appropriate type (float, int, or str)."""
    # If value is quoted, treat as string and strip quotes
    if (value_str.startswith('"') and value_str.endswith('"')) or (
        value_str.startswith("'") and value_str.endswith("'")
    ):
        return value_str[1:-1]

    try:
        # Try float first (handles decimals)
        if "." in value_str:
            return float(value_str)
        # Try int if no decimal point
        return int(value_str)
    except ValueError:
        # Default to string
        return value_str


class GraphRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for graph browsing."""

    def __init__(self, *args, server_config: dict[str, Any] | None = None, **kwargs):
        self.server_config = server_config or {}
        super().__init__(*args, **kwargs)

    def do_GET(self) -> None:
        """Handle GET requests."""
        try:
            # Parse the URL
            parsed_url = urlparse(self.path)

            if parsed_url.path != "/":
                self.send_error(404, "Only / endpoint is supported")
                return

            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            vertex_props: dict[str, str | int | float] = {}

            for key, values in query_params.items():
                # Take the first value for each parameter
                if values:
                    vertex_props[key] = parse_value(values[0])

            # Get edges for this vertex if providers are available
            edges_data = None
            vertex_validation = None

            provider_manager = self.server_config.get("provider_manager")
            if provider_manager and vertex_props:
                try:
                    # Validate vertex properties against available providers
                    is_valid, validation_msg = (
                        provider_manager.validate_vertex_for_providers(vertex_props)
                    )
                    vertex_validation = {
                        "is_valid": is_valid,
                        "message": validation_msg,
                    }

                    if is_valid:
                        # Create vertex and get edges from all providers
                        vertex = Vertex(vertex_props)
                        edges_data = []

                        # Try each provider to get edges
                        for (
                            provider_name,
                            provider,
                        ) in provider_manager.providers.items():
                            try:
                                provider_edges = list(provider(vertex))

                                for target_vertex, edge in provider_edges:
                                    # Extract edge information
                                    edge_info = {
                                        "target_vertex": dict(target_vertex),
                                        "cost": getattr(edge, "cost", None),
                                        "metadata": getattr(edge, "metadata", {}),
                                        "provider": provider_name,
                                    }
                                    edges_data.append(edge_info)

                            except Exception as provider_error:
                                print(
                                    f"Provider {provider_name} error: {provider_error}"
                                )

                        print(
                            f"Found {len(edges_data)} total edges for vertex {vertex_props}"
                        )

                except Exception as e:
                    print(f"Error getting edges: {e}")
                    vertex_validation = {
                        "is_valid": False,
                        "message": f"Error processing vertex: {e}",
                    }

            # Generate HTML response with edge data
            html_content = generate_html_response(
                vertex_props,
                self.server_config,
                edges_data=edges_data,
                vertex_validation=vertex_validation,
            )

            # Send response
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html_content.encode("utf-8"))

        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")

    def log_message(self, format: str, *args: Any) -> None:
        """Custom log message to show requests."""
        print(f"[{self.address_string()}] {format % args}")
