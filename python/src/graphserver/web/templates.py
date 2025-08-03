"""HTML template generation for the graph web browser."""
# ruff: noqa: T201

from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

if TYPE_CHECKING:
    from graphserver import GraphserverDataType


def _load_template(name: str) -> Template:
    """Load HTML template from templates directory."""
    template_path = Path(__file__).parent / "templates" / f"{name}.html"
    return Template(template_path.read_text())


def _load_css() -> str:
    """Load CSS from static directory."""
    css_path = Path(__file__).parent / "static" / "style.css"
    return css_path.read_text()


def generate_html_response(
    vertex_props: dict[str, GraphserverDataType],
    server_config: dict[str, Any],
    edges_data: list[dict[str, Any]] | None = None,
    vertex_validation: dict[str, Any] | None = None,
) -> str:
    """Generate complete HTML response for the given vertex properties."""
    # Load templates
    base_template = _load_template("base")
    css_content = _load_css()

    # Format vertex properties as JSON
    vertex_json = json.dumps(vertex_props, indent=4) if vertex_props else "{}"

    # Determine page content
    if not vertex_props:
        # Root page - show usage instructions
        content_section = generate_usage_content(server_config)
    else:
        # Vertex page - show vertex and edges
        content_section = generate_vertex_content(
            vertex_json, edges_data, vertex_validation
        )

    # Render the complete page
    return base_template.substitute(css_content=css_content, content=content_section)


def generate_usage_content(server_config: dict[str, Any]) -> str:
    """Generate usage instructions for the root page."""
    usage_template = _load_template("usage")

    osm_files = server_config.get("osm_files", [])
    gtfs_files = server_config.get("gtfs_files", [])

    config_info = ""
    if osm_files or gtfs_files:
        config_items = []
        if osm_files:
            config_items.append(f"OSM files: {', '.join(osm_files)}")
        if gtfs_files:
            config_items.append(f"GTFS files: {', '.join(gtfs_files)}")
        config_info = f"""
    <div class="config">
        <h3>Server Configuration</h3>
        <p>{" | ".join(config_items)}</p>
    </div>"""

    # Generate provider samples section
    provider_samples_info = _generate_provider_samples_section(server_config)

    return usage_template.substitute(
        config_info=config_info, provider_samples_info=provider_samples_info
    )


def _generate_provider_samples_section(server_config: dict[str, Any]) -> str:
    """Generate HTML section showing sample vertices for each provider."""
    from .providers import ProviderManager

    provider_manager = server_config.get("provider_manager")
    if not isinstance(provider_manager, ProviderManager):
        return ""  # No provider manager available

    try:
        # Get sample vertices from all providers
        provider_samples = provider_manager.get_sample_vertices_for_providers(
            max_samples=5
        )

        if not provider_samples:
            return ""  # No providers or no samples

        # Generate HTML for provider samples
        provider_sections = []

        for provider_name, sample_vertices in provider_samples.items():
            if not sample_vertices:
                continue  # Skip providers with no samples

            # Generate sample vertex links
            sample_links = []
            for i, vertex_data in enumerate(sample_vertices, 1):
                link_html = _generate_sample_vertex_link(vertex_data, i)
                sample_links.append(link_html)

            if sample_links:
                provider_section = f"""
                <div class="provider-section">
                    <h4>{provider_name}</h4>
                    <div class="sample-vertices">
                        {"".join(sample_links)}
                    </div>
                </div>"""
                provider_sections.append(provider_section)

        if provider_sections:
            return f"""
            <div class="providers">
                <h3>Available Providers & Sample Vertices</h3>
                {"".join(provider_sections)}
            </div>"""

    except Exception as e:  # noqa: BLE001
        # Graceful fallback if provider samples fail
        print(f"Warning: Failed to generate provider samples: {e}")

    return ""


def _format_provider_name(provider_name: str) -> str:
    """Format provider name for display."""
    # Convert snake_case to Title Case
    name_parts = provider_name.replace("_", " ").split()
    return " ".join(word.capitalize() for word in name_parts)


def _generate_sample_vertex_link(vertex_data: dict[str, Any], index: int) -> str:
    """Generate HTML link for a sample vertex."""
    # Create query string from vertex data
    query_params = []
    for key, value in vertex_data.items():
        if key == "_hash":
            continue  # Skip internal hash field
        if isinstance(value, str):
            # Quote string values to preserve them
            query_params.append(f"{key}={quote('"' + str(value) + '"')}")
        else:
            query_params.append(f"{key}={value}")

    query_string = "&".join(query_params)

    # Format vertex data for display (compact JSON)
    display_data = {k: v for k, v in vertex_data.items() if k != "_hash"}
    vertex_display = json.dumps(display_data, separators=(",", ":"))

    return f"""
    <div class="sample-vertex">
        <a href="/?{query_string}" class="link">
            {vertex_display}
        </a>
    </div>"""


def generate_vertex_content(
    vertex_json: str,
    edges_data: list[dict[str, Any]] | None = None,
    vertex_validation: dict[str, Any] | None = None,
) -> str:
    """Generate content for a specific vertex."""
    vertex_template = _load_template("vertex")

    # Generate edges section
    edges_section = _generate_edges_section(edges_data, vertex_validation)

    return vertex_template.substitute(
        vertex_json=vertex_json, edges_section=edges_section
    )


def _generate_edges_section(
    edges_data: list[dict[str, Any]] | None, vertex_validation: dict[str, Any] | None
) -> str:
    """Generate the edges section of the vertex page."""
    if vertex_validation and not vertex_validation.get("is_valid", True):
        # Show validation error
        return f"""
    <div class="edges">
        <h2>Vertex Validation</h2>
        <div class="error">
            <p><strong>❌ Invalid vertex:</strong> {vertex_validation["message"]}</p>
        </div>
    </div>"""

    if not edges_data:
        # No edges found
        return """
    <div class="edges">
        <h2>Outbound Edges</h2>
        <p><em>No outbound edges found from this vertex.</em></p>
        <p>This could mean:</p>
        <ul>
            <li>The vertex is not connected to the graph</li>
            <li>The vertex properties don't match provider patterns</li>
            <li>The location is outside the loaded data bounds</li>
        </ul>
    </div>"""

    # Generate edge list
    edges_html = []
    for edge_info in edges_data:
        target = edge_info["target_vertex"]
        cost = edge_info.get("cost", "Unknown")
        metadata = edge_info.get("metadata", {})
        provider = edge_info.get("provider", "unknown")

        # Create query string for target vertex
        query_params = []
        for key, value in target.items():
            if isinstance(value, str):
                query_params.append(f"{key}={quote('"' + str(value) + '"')}")
            else:
                query_params.append(f"{key}={value}")

        query_string = "&".join(query_params)
        target_json = json.dumps(target, separators=(",", ": "))

        # Format cost display
        cost_display = f"cost: {cost}" if cost is not None else "cost: unknown"

        # Get edge type and icon
        edge_type = metadata.get("edge_type", "unknown")

        # Generate metadata display
        metadata_html = ""
        if metadata:
            metadata_items = []
            for key, value in metadata.items():
                if key != "edge_type":  # Don't duplicate edge type
                    metadata_items.append(f"<li><strong>{key}:</strong> {value}</li>")

            if metadata_items:
                metadata_html = f"""
                <div class="edge-metadata">
                    <div class="edge-type-badge edge-{provider}">
                        {edge_type}
                    </div>
                    <ul class="metadata-list">
                        {"".join(metadata_items)}
                        <li><strong>provider:</strong> {provider}</li>
                    </ul>
                </div>"""

        edges_html.append(f"""
        <div class="edge edge-{provider}">
            <div class="edge-link">
                → <a href="/?{query_string}" class="link">{target_json}</a>
                <small>({cost_display})</small>
            </div>
            {metadata_html}
        </div>""")

    edges_list = "".join(edges_html)

    return f"""
    <div class="edges">
        <h2>Outbound Edges ({len(edges_data)} found)</h2>
        {edges_list}
    </div>"""
