#!/usr/bin/env python3
"""Graph Web Server - Main server implementation and CLI entry point."""

from __future__ import annotations

import argparse
import sys
from http.server import HTTPServer
from typing import Sequence

from .handlers import GraphRequestHandler


class GraphWebServer:
    """Web server for graph browsing."""

    def __init__(self, port: int, osm_files: Sequence[str] | None = None,
                 gtfs_files: Sequence[str] | None = None):
        self.port = port
        self.osm_files = list(osm_files or [])
        self.gtfs_files = list(gtfs_files or [])
        self.server_config = {
            'osm_files': self.osm_files,
            'gtfs_files': self.gtfs_files
        }

    def run(self) -> None:
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


def main() -> None:
    """Main entry point for the CLI."""
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