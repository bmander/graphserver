"""HTML template generation for the graph web browser."""

from __future__ import annotations

import json
from typing import Any


def generate_html_response(vertex_props: dict[str, Any],
                           server_config: dict[str, Any]) -> str:
    """Generate complete HTML response for the given vertex properties."""
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

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <title>Graph Browser</title>
    <style>
        body {{
            font-family: monospace;
            margin: 20px;
            background-color: #fafafa;
        }}
        .header {{
            border-bottom: 2px solid #333;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .vertex {{
            background: #f0f0f0;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
        .edges {{
            margin-left: 20px;
        }}
        .edge {{
            margin: 5px 0;
            padding: 5px;
            background: #fff;
            border-left: 3px solid #007acc;
            padding-left: 10px;
        }}
        .link {{
            color: #007acc;
            text-decoration: underline;
            cursor: pointer;
        }}
        .link:hover {{
            background-color: #e6f3ff;
        }}
        .usage {{
            background: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #b8dce8;
            margin-bottom: 20px;
        }}
        .example {{
            background: #fff;
            padding: 10px;
            margin: 10px 0;
            border-radius: 3px;
            border: 1px solid #ddd;
        }}
        pre {{
            margin: 0;
            white-space: pre-wrap;
        }}
        .config {{
            background: #fff3cd;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ffeaa7;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Graph Browser</h1>
        <p>Explore graph vertices and their outbound edges</p>
    </div>

    {content_section}
</body>
</html>"""

    return html_template


def generate_usage_content(server_config: dict[str, Any]) -> str:
    """Generate usage instructions for the root page."""
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

    return f"""{config_info}
    <div class="usage">
        <h2>How to Use</h2>
        <p>Add query parameters to explore vertices. Parameters are automatically
        converted to appropriate types:</p>
        <ul>
            <li><strong>Numbers with decimals</strong> become floats
                (e.g., lat=47.6)</li>
            <li><strong>Whole numbers</strong> become integers
                (e.g., osm_node_id=12345)</li>
            <li><strong>Everything else</strong> becomes strings
                (e.g., mode=walk)</li>
        </ul>
    </div>

    <div class="edges">
        <h2>Example Queries</h2>

        <div class="example">
            <strong>Coordinate-based vertex:</strong><br>
            <a href="/?lat=47.6&lon=-122.3" class="link">
                /?lat=47.6&lon=-122.3</a>
        </div>

        <div class="example">
            <strong>OSM node vertex:</strong><br>
            <a href="/?osm_node_id=12345" class="link">/?osm_node_id=12345</a>
        </div>

        <div class="example">
            <strong>Transit stop with time:</strong><br>
            <a href="/?stop_id=STOP123&time=1234567890" class="link">
                /?stop_id=STOP123&time=1234567890</a>
        </div>

        <div class="example">
            <strong>Mixed parameters:</strong><br>
            <a href="/?lat=47.6&lon=-122.3&mode=walk" class="link">
                /?lat=47.6&lon=-122.3&mode=walk</a>
        </div>
    </div>"""


def generate_vertex_content(vertex_json: str) -> str:
    """Generate content for a specific vertex."""
    return f"""
    <div class="vertex">
        <h2>Current Vertex</h2>
        <pre>{vertex_json}</pre>
    </div>

    <div class="edges">
        <h2>Outbound Edges</h2>
        <p><em>Phase 1: Edge providers not yet implemented.
           Coming in Phase 2!</em></p>
        <p>This vertex would be processed by graph engine to find
           adjacent vertices.</p>
    </div>"""
