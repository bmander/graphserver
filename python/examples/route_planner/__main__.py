"""Route planner web application entry point."""

import argparse
import sys
from pathlib import Path

from .server import RoutePlannerServer


def main() -> None:
    """Main entry point for the route planner application."""
    parser = argparse.ArgumentParser(
        description="Interactive route planner web application",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m route_planner --osm examples/uw_campus.osm
  python -m route_planner --osm city.osm --gtfs transit.zip --port 8080
        """,
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Server port (default: 8080)",
    )

    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)",
    )

    parser.add_argument(
        "--osm",
        required=True,
        help="OSM file path (required)",
    )

    parser.add_argument(
        "--gtfs",
        action="append",
        dest="gtfs_files",
        help="GTFS file path (can be specified multiple times)",
    )

    args = parser.parse_args()

    # Validate port range
    max_port = 65535
    if not (1 <= args.port <= max_port):
        print(f"Error: Port must be between 1 and {max_port}, got {args.port}")
        sys.exit(1)

    # Validate OSM file exists
    osm_path = Path(args.osm)
    if not osm_path.exists():
        print(f"Error: OSM file not found: {args.osm}")
        sys.exit(1)

    # Validate GTFS files exist (if provided)
    if args.gtfs_files:
        for gtfs_file in args.gtfs_files:
            gtfs_path = Path(gtfs_file)
            if not gtfs_path.exists():
                print(f"Error: GTFS file not found: {gtfs_file}")
                sys.exit(1)

    # Create and run server
    try:
        server = RoutePlannerServer(
            host=args.host,
            port=args.port,
            osm_file=args.osm,
            gtfs_files=args.gtfs_files,
        )
        server.run()
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Error: Port {args.port} is already in use")
            print("Try using a different port with --port")
        else:
            print(f"❌ Server error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
