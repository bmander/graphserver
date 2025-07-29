"""HTTP request handlers for the graph web browser."""
# ruff: noqa: T201

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

    def _parse_vertex_from_request(self) -> dict[str, str | int | float] | None:
        """Parse vertex properties from the request URL.

        Returns:
            Dict of vertex properties, or None if URL is invalid
        """
        # Parse the URL
        parsed_url = urlparse(self.path)

        if parsed_url.path != "/":
            self.send_error(404, "Only / endpoint is supported")
            return None

        # Parse query parameters
        query_params = parse_qs(parsed_url.query)
        vertex_props: dict[str, str | int | float] = {}

        for key, values in query_params.items():
            # Take the first value for each parameter
            if values:
                vertex_props[key] = parse_value(values[0])

        return vertex_props

    def _get_edges_from_provider(
        self, provider_name: str, provider, vertex
    ) -> list[dict]:
        """Get edges from a single provider.

        Args:
            provider_name: Name of the provider
            provider: Provider instance
            vertex: Vertex to get edges for

        Returns:
            List of edge info dicts
        """
        edges_data = []
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

        except Exception as provider_error:  # noqa: BLE001
            print(f"Provider {provider_name} error: {provider_error}")

        return edges_data

    def _process_vertex_with_providers(
        self, vertex_props: dict, provider_manager
    ) -> tuple[list[dict] | None, dict]:
        """Process vertex with all available providers.

        Args:
            vertex_props: Vertex properties dict
            provider_manager: Provider manager instance

        Returns:
            Tuple of (edges_data, vertex_validation)
        """
        if not provider_manager or not vertex_props:
            return None, {
                "is_valid": False,
                "message": "No provider manager or vertex properties",
            }

        try:
            # Validate vertex properties against available providers
            is_valid, validation_msg = provider_manager.validate_vertex_for_providers(
                vertex_props
            )
            vertex_validation = {
                "is_valid": is_valid,
                "message": validation_msg,
            }

            if not is_valid:
                return None, vertex_validation

            # Create vertex and get edges from all providers
            vertex = Vertex(vertex_props)
            edges_data = []

            # Try each provider to get edges
            for provider_name, provider in provider_manager.providers.items():
                provider_edges = self._get_edges_from_provider(
                    provider_name, provider, vertex
                )
                edges_data.extend(provider_edges)

            print(f"Found {len(edges_data)} total edges for vertex {vertex_props}")

        except Exception as e:  # noqa: BLE001
            print(f"Error getting edges: {e}")
            vertex_validation = {
                "is_valid": False,
                "message": f"Error processing vertex: {e}",
            }
            return None, vertex_validation
        else:
            return edges_data, vertex_validation

    def _send_html_response(
        self,
        vertex_props: dict,
        edges_data: list[dict] | None,
        vertex_validation: dict | None,
    ) -> None:
        """Generate and send HTML response.

        Args:
            vertex_props: Vertex properties dict
            edges_data: List of edge data or None
            vertex_validation: Vertex validation info or None
        """
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

    def do_GET(self) -> None:  # noqa: N802
        """Handle GET requests."""
        try:
            # Parse vertex properties from the request
            vertex_props = self._parse_vertex_from_request()
            if vertex_props is None:
                return  # Error already sent in _parse_vertex_from_request

            # Process vertex with providers to get edges
            provider_manager = self.server_config.get("provider_manager")
            edges_data, vertex_validation = self._process_vertex_with_providers(
                vertex_props, provider_manager
            )

            # Send HTML response
            self._send_html_response(vertex_props, edges_data, vertex_validation)

        except Exception as e:  # noqa: BLE001
            self.send_error(500, f"Internal server error: {str(e)}")

    def log_message(self, fmt: str, *args: Any) -> None:
        """Custom log message to show requests."""
        print(f"[{self.address_string()}] {fmt % args}")
