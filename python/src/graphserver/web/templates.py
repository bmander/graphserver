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
                           server_config: dict[str, Any]) -> str:
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
        # Vertex page - show vertex and placeholder for edges
        content_section = generate_vertex_content(vertex_json)

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


def generate_vertex_content(vertex_json: str) -> str:
    """Generate content for a specific vertex."""
    vertex_template = _load_template("vertex")
    return vertex_template.substitute(vertex_json=vertex_json)