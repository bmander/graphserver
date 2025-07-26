"""HTML template generation for the graph web browser."""

from __future__ import annotations

import json
from pathlib import Path
from string import Template
from typing import Any


def _load_template(name: str) -> Template:
    """Load HTML template from templates directory."""
    template_path = Path(__file__).parent / "templates" / f"{name}.html"
    return Template(template_path.read_text())


def _load_css() -> str:
    """Load CSS from static directory."""
    css_path = Path(__file__).parent / "static" / "style.css"
    return css_path.read_text()


def generate_html_response(vertex_props: dict[str, Any],
                           server_config: dict[str, Any],
                           edges_data: list[dict] | None = None,
                           vertex_validation: dict[str, Any] | None = None) -> str:
    """Generate complete HTML response for the given vertex properties."""
    # Load templates
    base_template = _load_template("base")
    css_content = _load_css()

    # Format vertex properties as JSON
    vertex_json = (json.dumps(vertex_props, indent=4)
                   if vertex_props else "{}")

    # Determine page content
    if not vertex_props:
        # Root page - show usage instructions
        content_section = generate_usage_content(server_config)
    else:
        # Vertex page - show vertex and edges
        content_section = generate_vertex_content(
            vertex_json, 
            edges_data, 
            vertex_validation
        )

    # Render the complete page
    return base_template.substitute(
        css_content=css_content,
        content=content_section
    )


def generate_usage_content(server_config: dict[str, Any]) -> str:
    """Generate usage instructions for the root page."""
    usage_template = _load_template("usage")

    osm_files = server_config.get('osm_files', [])
    gtfs_files = server_config.get('gtfs_files', [])

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
        <p>{' | '.join(config_items)}</p>
    </div>"""

    return usage_template.substitute(config_info=config_info)


def generate_vertex_content(vertex_json: str,
                            edges_data: list[dict] | None = None,
                            vertex_validation: dict[str, Any] | None = None) -> str:
    """Generate content for a specific vertex."""
    vertex_template = _load_template("vertex")

    # Generate edges section
    edges_section = _generate_edges_section(edges_data, vertex_validation)

    return vertex_template.substitute(
        vertex_json=vertex_json,
        edges_section=edges_section
    )


def _generate_edges_section(edges_data: list[dict] | None,
                           vertex_validation: dict[str, Any] | None) -> str:
    """Generate the edges section of the vertex page."""
    if vertex_validation and not vertex_validation.get('is_valid', True):
        # Show validation error
        return f"""
    <div class="edges">
        <h2>Vertex Validation</h2>
        <div class="error">
            <p><strong>❌ Invalid vertex:</strong> {vertex_validation['message']}</p>
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
    for i, edge_info in enumerate(edges_data):
        target = edge_info['target_vertex']
        cost = edge_info.get('cost', 'Unknown')
        
        # Create query string for target vertex
        query_params = []
        for key, value in target.items():
            if isinstance(value, str):
                query_params.append(f"{key}={value}")
            else:
                query_params.append(f"{key}={value}")
        
        query_string = "&".join(query_params)
        target_json = json.dumps(target, separators=(',', ': '))
        
        # Format cost display
        cost_display = f"cost: {cost}" if cost is not None else "cost: unknown"
        
        edges_html.append(f"""
        <div class="edge">
            → <a href="/?{query_string}" class="link">{target_json}</a>
            <small>({cost_display})</small>
        </div>""")
    
    edges_list = "".join(edges_html)
    
    return f"""
    <div class="edges">
        <h2>Outbound Edges ({len(edges_data)} found)</h2>
        {edges_list}
    </div>"""
