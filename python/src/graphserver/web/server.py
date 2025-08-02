#!/usr/bin/env python3
"""Graph Web Server - Main server implementation and CLI entry point."""
# ruff: noqa: T201

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from http.server import HTTPServer
from typing import Any

from .handlers import GraphRequestHandler
from .providers import ProgressCallback, ProviderError, ProviderManager

# Network constants
MIN_PORT = 1
MAX_PORT = 65535


class GraphWebServer:
    """Web server for graph browsing."""

    def __init__(
        self,
        port: int,
        osm_files: Sequence[str] | None = None,
        gtfs_files: Sequence[str] | None = None,
    ):
        self.port = port
        self.osm_files = list(osm_files or [])
        self.gtfs_files = list(gtfs_files or [])

        # Initialize provider manager
        self.provider_manager = ProviderManager(
            osm_files=self.osm_files, gtfs_files=self.gtfs_files
        )

        # Server configuration for handlers
        self.server_config = {
            "osm_files": self.osm_files,
            "gtfs_files": self.gtfs_files,
            "provider_manager": self.provider_manager,
        }

    def run(self) -> None:
        """Start the HTTP server."""
        # Initialize providers before starting server
        try:
            # Create progress callback for CLI usage
            progress_callback = create_tqdm_progress_callback("Initializing providers")
            self.provider_manager.initialize_engine(progress_callback)
            print("✅ Provider initialization complete")

        except ProviderError as e:
            print(f"❌ Provider initialization failed: {e}")
            print("\nPlease check your file paths and try again.")
            sys.exit(1)

        # Create a handler class with server config
        def handler_factory(*args: Any, **kwargs: Any) -> GraphRequestHandler:
            return GraphRequestHandler(
                *args, server_config=self.server_config, **kwargs
            )

        try:
            server = HTTPServer(("localhost", self.port), handler_factory)
            print(f"\n🌐 Graph Web Browser started on http://localhost:{self.port}")

            # Show provider information
            provider_info = self.provider_manager.get_provider_info()
            if provider_info:
                print("\n📊 Active Providers:")
                for provider_type, info in provider_info.items():
                    print(f"  • {provider_type}: {info}")

            print(f"\n🚀 Ready to explore! Visit http://localhost:{self.port}")
            print("Press Ctrl+C to stop the server")
            server.serve_forever()

        except KeyboardInterrupt:
            print("\n👋 Server stopped by user")
        except OSError as e:
            print(f"❌ Error starting server: {e}")
            sys.exit(1)


def create_tqdm_progress_callback(task_name: str) -> ProgressCallback:
    """Create a progress callback that uses tqdm for CLI progress bars.

    Args:
        task_name: Name of the overall task for the progress bar

    Returns:
        A progress callback function that creates and manages a tqdm progress bar
    """
    try:
        from tqdm import tqdm
    except ImportError:
        # If tqdm is not available, return a simple print-based callback
        def simple_callback(description: str, current: int, total: int) -> None:
            percentage = (current / total * 100) if total > 0 else 0
            print(f"[{percentage:5.1f}%] {description}")

        return simple_callback

    bar = None

    def callback(description: str, current: int, total: int) -> None:
        nonlocal bar

        # Create bar on first call
        if bar is None:
            bar = tqdm(total=total, desc=task_name, unit="step")

        # Update progress bar
        bar.set_description(description)
        bar.n = current
        bar.refresh()

        # Close bar when complete
        if current >= total:
            bar.close()
            bar = None

    return callback


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description=(
            "Graph Web Browser - HTTP interface for exploring graph vertices and edges"
        )
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Server port (default: 8080)"
    )
    parser.add_argument(
        "--osm",
        action="append",
        dest="osm_files",
        help="OSM file path (can be specified multiple times)",
    )
    parser.add_argument(
        "--gtfs",
        action="append",
        dest="gtfs_files",
        help="GTFS file path (can be specified multiple times)",
    )

    args = parser.parse_args()

    # Validate port
    if not (MIN_PORT <= args.port <= MAX_PORT):
        print(f"Error: Port must be between {MIN_PORT} and {MAX_PORT}")
        sys.exit(1)

    # Create and run server
    server = GraphWebServer(
        port=args.port, osm_files=args.osm_files, gtfs_files=args.gtfs_files
    )

    server.run()


if __name__ == "__main__":
    main()
