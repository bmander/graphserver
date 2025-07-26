#!/usr/bin/env python3
"""
Graph Web Browser - HTTP interface for exploring graph vertices and edges.

Phase 1: Basic HTTP server with query parameter parsing and HTML responses.
"""

import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


def parse_value(value_str):
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

    def __init__(self, *args, server_config=None, **kwargs):
        self.server_config = server_config or {}
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        try:
            # Parse the URL
            parsed_url = urlparse(self.path)

            if parsed_url.path != '/':
                self.send_error(404, "Only / endpoint is supported")
                return

            # Parse query parameters
            query_params = parse_qs(parsed_url.query)
            vertex_props = {}

            for key, values in query_params.items():
                # Take the first value for each parameter
                if values:
                    vertex_props[key] = parse_value(values[0])

            # Generate HTML response
            html_content = self.generate_html_response(vertex_props)

            # Send response
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Internal server error: {str(e)}")

    def generate_html_response(self, vertex_props):
        """Generate HTML response for the given vertex properties."""
        # Format vertex properties as JSON
        vertex_json = (json.dumps(vertex_props, indent=4)
                       if vertex_props else "{}")

        # Determine page content
        if not vertex_props:
            # Root page - show usage instructions
            content_section = self.generate_usage_content()
        else:
            # Vertex page - show vertex and placeholder for edges
            content_section = self.generate_vertex_content(vertex_json)

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

    def generate_usage_content(self):
        """Generate usage instructions for the root page."""
        osm_files = self.server_config.get('osm_files', [])
        gtfs_files = self.server_config.get('gtfs_files', [])

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

    def generate_vertex_content(self, vertex_json):
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

    def log_message(self, format, *args):
        """Custom log message to show requests."""
        print(f"[{self.address_string()}] {format % args}")


class GraphWebServer:
    """Web server for graph browsing."""

    def __init__(self, port, osm_files=None, gtfs_files=None):
        self.port = port
        self.osm_files = osm_files or []
        self.gtfs_files = gtfs_files or []
        self.server_config = {
            'osm_files': self.osm_files,
            'gtfs_files': self.gtfs_files
        }

    def run(self):
        """Start the HTTP server."""
        # Create a handler class with server config
        def handler_factory(*args, **kwargs):
            return GraphRequestHandler(*args,
                                       server_config=self.server_config,
                                       **kwargs)

        try:
            server = HTTPServer(('localhost', self.port), handler_factory)
            print(f"Graph Web Browser started on "
                  f"http://localhost:{self.port}")

            if self.osm_files:
                print(f"OSM files: {', '.join(self.osm_files)}")
            if self.gtfs_files:
                print(f"GTFS files: {', '.join(self.gtfs_files)}")

            print("Press Ctrl+C to stop the server")
            server.serve_forever()

        except KeyboardInterrupt:
            print("\nServer stopped by user")
        except OSError as e:
            print(f"Error starting server: {e}")
            sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description=('Graph Web Browser - HTTP interface for '
                     'exploring graph vertices and edges')
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Server port (default: 8080)'
    )
    parser.add_argument(
        '--osm',
        action='append',
        dest='osm_files',
        help='OSM file path (can be specified multiple times)'
    )
    parser.add_argument(
        '--gtfs',
        action='append',
        dest='gtfs_files',
        help='GTFS file path (can be specified multiple times)'
    )

    args = parser.parse_args()

    # Validate port
    if not (1 <= args.port <= 65535):
        print("Error: Port must be between 1 and 65535")
        sys.exit(1)

    # Create and run server
    server = GraphWebServer(
        port=args.port,
        osm_files=args.osm_files,
        gtfs_files=args.gtfs_files
    )

    server.run()


if __name__ == '__main__':
    main()
