"""Provider initialization and management for the graph web browser."""
# ruff: noqa: T201

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from graphserver import Engine

if TYPE_CHECKING:
    from graphserver.core import EdgeProvider


class ProviderError(Exception):
    """Raised when provider initialization fails."""


class ProviderManager:
    """Manages provider initialization and engine configuration."""

    def __init__(
        self,
        osm_files: Sequence[str] | None = None,
        gtfs_files: Sequence[str] | None = None,
    ):
        self.osm_files = list(osm_files or [])
        self.gtfs_files = list(gtfs_files or [])
        self.engine: Engine | None = None
        self.providers: dict[str, EdgeProvider] = {}

        # Cross-modal linking statistics
        self.linking_stats = {"total_stops": 0, "linked_stops": 0, "failed_links": []}

    def initialize_engine(self) -> Engine:
        """Initialize the graph engine with all configured providers."""
        if self.engine is not None:
            return self.engine

        # Create engine with caching enabled for performance
        self.engine = Engine(enable_edge_caching=True)

        # Initialize and register providers in order of specificity
        # More specific providers first (transit, then OSM access, then OSM network)

        try:
            # Initialize Transit providers if GTFS files specified
            if self.gtfs_files:
                self._initialize_transit_providers()

            # Initialize OSM providers if OSM files specified
            if self.osm_files:
                self._initialize_osm_providers()

            if not self.providers:
                msg = "No providers initialized. Please specify --osm or --gtfs files."
                raise ProviderError(msg)  # noqa: TRY301
            else:  # noqa: RET506
                print(f"Initialized {len(self.providers)} provider(s)")
                return self.engine

        except Exception as e:
            msg = f"Failed to initialize providers: {e}"
            raise ProviderError(msg) from e

    def _validate_transit_imports(self) -> None:
        """Validate that required imports are available for transit providers."""
        try:
            from graphserver.providers.transit import TransitProvider  # noqa: F401
        except ImportError as e:
            msg = (
                "Transit provider not available. Install with: "
                "pip install graphserver[transit]"
            )
            raise ProviderError(msg) from e

        try:
            from tqdm import tqdm  # noqa: F401
        except ImportError as e:
            msg = (
                "tqdm not available for progress bars. Install with: "
                "pip install graphserver[web]"
            )
            raise ProviderError(msg) from e

    def _create_progress_callback(self, pbar):
        """Create progress callback function for updating progress bar."""

        def progress_callback(
            step_name: str,
            current_step: int,
            total_steps: int,
            sub_progress: float | None = None,
        ) -> None:  # noqa: ARG001
            if sub_progress is not None:
                # Update postfix with sub-progress info, don't advance main
                pbar.set_postfix_str(step_name)
            else:
                # Step complete, advance main progress
                pbar.set_postfix_str(step_name)
                pbar.update(1)

        return progress_callback

    def _validate_gtfs_file(self, gtfs_path: Path) -> None:
        """Validate that GTFS file exists and is a valid zip file."""
        if not gtfs_path.exists():
            msg = f"GTFS file not found: {gtfs_path}"
            raise ProviderError(msg)

        if not (gtfs_path.is_file() and gtfs_path.suffix.lower() == ".zip"):
            msg = f"GTFS file must be a .zip file: {gtfs_path}"
            raise ProviderError(msg)

    def _register_transit_provider(
        self, transit_provider, provider_name: str, pbar
    ) -> dict:
        """Register transit provider and collect statistics."""
        pbar.set_postfix_str("Registering provider...")
        self.providers[provider_name] = transit_provider
        self.engine.register_provider(provider_name, transit_provider)

        # Collect statistics for this feed
        feed_stops = transit_provider.parser.stop_count
        feed_routes = transit_provider.parser.route_count
        feed_trips = transit_provider.parser.trip_count

        pbar.set_postfix_str(
            f"stops: {feed_stops}, routes: {feed_routes}, trips: {feed_trips}"
        )
        pbar.update(1)

        return {"stops": feed_stops, "routes": feed_routes, "trips": feed_trips}

    def _print_transit_summary(
        self, total_stops: int, total_routes: int, total_trips: int
    ) -> None:
        """Print summary of loaded GTFS providers."""
        if len(self.gtfs_files) == 1:
            print(
                f"✅ Registered GTFS provider: "
                f"{total_stops} stops, {total_routes} routes, {total_trips} trips"
            )
        else:
            print(
                f"✅ Registered {len(self.gtfs_files)} GTFS providers: "
                f"{total_stops} total stops, {total_routes} total routes, "
                f"{total_trips} total trips"
            )

    def _validate_osm_imports(self) -> None:
        """Validate that required imports are available for OSM providers."""
        try:
            from graphserver.providers.osm import (  # noqa: F401
                OSMAccessProvider,
                OSMNetworkProvider,
            )
        except ImportError as e:
            msg = (
                "OSM providers not available. Install with: "
                "pip install graphserver[osm]"
            )
            raise ProviderError(msg) from e

        try:
            from tqdm import tqdm  # noqa: F401
        except ImportError as e:
            msg = (
                "tqdm not available for progress bars. Install with: "
                "pip install graphserver[web]"
            )
            raise ProviderError(msg) from e

    def _validate_osm_file(self, osm_path: Path) -> None:
        """Validate that OSM file exists and is a valid file."""
        if not osm_path.exists():
            msg = f"OSM file not found: {osm_path}"
            raise ProviderError(msg)

        if not osm_path.is_file():
            msg = f"OSM path must be a file: {osm_path}"
            raise ProviderError(msg)

    def _create_osm_providers(self, osm_path: Path) -> tuple:
        """Create OSM providers and return statistics."""
        from tqdm import tqdm

        from graphserver.providers.osm import OSMAccessProvider, OSMNetworkProvider
        from graphserver.providers.osm.parser import OSMParser
        from graphserver.providers.osm.types import WalkingProfile

        # Get file size for context
        file_size_mb = osm_path.stat().st_size / (1024 * 1024)
        size_info = f"{file_size_mb:.1f}MB"

        # Initialize progress bar for OSM loading (4 detailed steps)
        with tqdm(
            total=4, desc=f"Loading OSM ({osm_path.name}, {size_info})", unit="step"
        ) as pbar:
            # Step 1: Parse OSM file
            pbar.set_postfix_str("Parsing OSM file...")
            parser = OSMParser(WalkingProfile())
            parser.parse_file(str(osm_path))
            pbar.update(1)

            # Step 2: Show parsing results
            raw_nodes = len(parser.nodes)
            raw_ways = len(parser.ways)
            raw_edges = len(parser.edges)
            pbar.set_postfix_str(
                f"nodes: {raw_nodes}, ways: {raw_ways}, edges: {raw_edges}"
            )
            pbar.update(1)

            # Step 3: Create OSM network provider (handles osm_node_id vertices)
            pbar.set_postfix_str("Creating network provider...")
            osm_network = OSMNetworkProvider(parser=parser)
            self.providers["osm_network"] = osm_network
            self.engine.register_provider("osm_network", osm_network)
            pbar.update(1)

            # Step 4: Create OSM access provider (handles lat/lon vertices)
            pbar.set_postfix_str("Creating access provider...")
            osm_access = OSMAccessProvider(parser=parser)
            self.providers["osm_access"] = osm_access
            self.engine.register_provider("osm_access", osm_access)
            pbar.update(1)
            pbar.set_postfix_str("Complete")

        return osm_access, {"nodes": raw_nodes, "ways": raw_ways, "edges": raw_edges}

    def _print_osm_summary(self, stats: dict, osm_path: Path) -> None:
        """Print summary of loaded OSM providers."""
        print(
            f"✅ Registered OSM providers: {stats['nodes']} nodes, "
            f"{stats['ways']} ways, {stats['edges']} edges ({osm_path.name})"
        )

    def _process_single_gtfs_file(self, i: int, gtfs_file: str, pbar) -> dict:
        """Process a single GTFS file and return statistics."""
        from graphserver.providers.transit import TransitProvider

        gtfs_path = Path(gtfs_file)
        pbar.set_description(f"Loading GTFS ({gtfs_path.name})")

        self._validate_gtfs_file(gtfs_path)

        try:
            # Create progress callback that updates our progress bar
            progress_callback = self._create_progress_callback(pbar)

            # Parse GTFS data with detailed progress
            provider_name = f"transit_{i}" if i > 0 else "transit"
            transit_provider = TransitProvider(
                str(gtfs_path), progress_callback=progress_callback
            )

            # Register provider and collect statistics
            return self._register_transit_provider(
                transit_provider, provider_name, pbar
            )

        except Exception as e:
            msg = f"Failed to initialize GTFS file {gtfs_file}: {e}"
            raise ProviderError(msg) from e

    def _initialize_transit_providers(self) -> None:
        """Initialize GTFS transit providers."""
        self._validate_transit_imports()
        from tqdm import tqdm

        # Initialize progress bar for GTFS loading (9 steps per file + 1 register step)
        total_steps = len(self.gtfs_files) * 10  # 9 parsing steps + 1 register step
        total_stops = 0
        total_routes = 0
        total_trips = 0

        with tqdm(total=total_steps, desc="Loading GTFS", unit="step") as pbar:
            for i, gtfs_file in enumerate(self.gtfs_files):
                feed_stats = self._process_single_gtfs_file(i, gtfs_file, pbar)
                total_stops += feed_stats["stops"]
                total_routes += feed_stats["routes"]
                total_trips += feed_stats["trips"]
            pbar.set_postfix_str("Complete")

        # Print detailed summary
        self._print_transit_summary(total_stops, total_routes, total_trips)

    def _initialize_osm_providers(self) -> None:
        """Initialize OSM routing providers."""
        self._validate_osm_imports()

        # For now, use the first OSM file for the main providers
        # Multiple OSM file support tracked in: https://github.com/bmander/graphserver/issues/50
        osm_file = self.osm_files[0]
        osm_path = Path(osm_file)

        self._validate_osm_file(osm_path)

        try:
            osm_access, stats = self._create_osm_providers(osm_path)
            self._print_osm_summary(stats, osm_path)

        except Exception as e:
            msg = f"Failed to initialize OSM file {osm_file}: {e}"
            raise ProviderError(msg) from e

        # Log additional OSM files that aren't yet supported
        if len(self.osm_files) > 1:
            print(f"Note: Multiple OSM files specified, but only using: {osm_file}")
            print("Multiple OSM file support will be added in a future version.")

        # Link transit stops to OSM network for cross-modal routing
        if self.gtfs_files and osm_access:
            self._link_transit_stops_to_osm(osm_access)

    def _get_transit_providers_for_linking(self) -> dict[str, any]:
        """Get transit providers that have stops available for linking."""
        transit_providers = {
            name: provider
            for name, provider in self.providers.items()
            if name.startswith("transit")
        }

        if not transit_providers:
            print("⚠️  No transit providers found for linking")
            return {}

        # Filter providers that have stops
        valid_providers = {}
        for provider_name, provider in transit_providers.items():
            if not hasattr(provider, "parser") or not hasattr(provider.parser, "stops"):
                print(f"⚠️  Transit provider {provider_name} has no stops to link")
                continue
            valid_providers[provider_name] = provider

        return valid_providers

    def _link_single_stop(self, stop, osm_access_provider) -> tuple[bool, str | None]:
        """Link a single transit stop to the OSM network.

        Args:
            stop: Transit stop object with stop_id, lat, lon
            osm_access_provider: The OSM access provider to use for linking

        Returns:
            Tuple of (success: bool, error_message: str | None)
        """
        from graphserver import Vertex

        try:
            # Create stop vertex for linking
            # (using only stop_id, no coordinates)
            stop_vertex = Vertex({"stop_id": stop.stop_id})

            # Link to nearest OSM node using stop coordinates
            osm_access_provider.link(stop_vertex, stop.lat, stop.lon)

        except ValueError as e:
            # Stop too far from OSM network
            return False, f"Stop {stop.stop_id}: {str(e)}"
        except Exception as e:  # noqa: BLE001
            # Unexpected error
            return False, f"Stop {stop.stop_id}: Unexpected error - {str(e)}"
        else:
            return True, None

    def _print_linking_summary(self) -> None:
        """Print summary of transit stop linking results."""
        total_stops = self.linking_stats["total_stops"]
        linked_stops = self.linking_stats["linked_stops"]
        failed_count = len(self.linking_stats["failed_links"])

        if total_stops > 0:
            success_rate = (linked_stops / total_stops) * 100
            print(
                f"✅ Linked {linked_stops}/{total_stops} transit stops to OSM network "
                f"({success_rate:.1f}%)"
            )

            if failed_count > 0:
                print(
                    f"⚠️  {failed_count} stops could not be linked "
                    f"(too far from OSM nodes)"
                )
                # Show first few failures as examples
                if failed_count <= 3:
                    for error in self.linking_stats["failed_links"]:
                        print(f"     {error}")
                else:
                    for error in self.linking_stats["failed_links"][:3]:
                        print(f"     {error}")
                    print(f"     ... and {failed_count - 3} more")
        else:
            print("⚠️  No transit stops found to link")

    def _link_transit_stops_to_osm(self, osm_access_provider) -> None:
        """Link all transit stops to nearby OSM nodes for multimodal routing.

        Args:
            osm_access_provider: The OSM access provider to use for linking
        """
        try:
            from tqdm import tqdm
        except ImportError as e:
            msg = (
                "tqdm not available for progress bars. Install with: "
                "pip install graphserver[web]"
            )
            raise ProviderError(msg) from e

        # Reset statistics
        self.linking_stats = {"total_stops": 0, "linked_stops": 0, "failed_links": []}

        # Get valid transit providers
        transit_providers = self._get_transit_providers_for_linking()
        if not transit_providers:
            return

        # Count total stops for progress bar
        total_stops = sum(
            len(provider.parser.stops) for provider in transit_providers.values()
        )

        # Link stops from all transit providers with progress bar
        with tqdm(
            total=total_stops, desc="Linking GTFS stops to OSM", unit="stop"
        ) as pbar:
            for provider_name, transit_provider in transit_providers.items():
                provider_linked = 0
                provider_total = 0

                for stop in transit_provider.parser.stops.values():
                    provider_total += 1
                    self.linking_stats["total_stops"] += 1

                    pbar.set_postfix_str(f"Stop {stop.stop_id}")

                    success, error_msg = self._link_single_stop(
                        stop, osm_access_provider
                    )
                    if success:
                        provider_linked += 1
                        self.linking_stats["linked_stops"] += 1
                    else:
                        self.linking_stats["failed_links"].append(error_msg)

                    pbar.update(1)

                pbar.set_description(
                    f"Linking stops ({provider_name}: "
                    f"{provider_linked}/{provider_total})"
                )

            pbar.set_postfix_str("Complete")

        # Print summary
        self._print_linking_summary()

    def get_provider_info(self) -> dict[str, str]:
        """Get information about initialized providers for display."""
        info = {}

        if self.osm_files:
            info["OSM"] = f"{len(self.osm_files)} file(s): {', '.join(self.osm_files)}"

        if self.gtfs_files:
            info["GTFS"] = (
                f"{len(self.gtfs_files)} file(s): {', '.join(self.gtfs_files)}"
            )

        # Add cross-modal linking information if available
        if self.osm_files and self.gtfs_files and self.linking_stats["total_stops"] > 0:
            linked_stops = self.linking_stats["linked_stops"]
            total_stops = self.linking_stats["total_stops"]
            success_rate = (linked_stops / total_stops) * 100 if total_stops > 0 else 0
            info["Cross-modal links"] = (
                f"{linked_stops}/{total_stops} transit stops linked to OSM network "
                f"({success_rate:.1f}%)"
            )

        return info

    def validate_vertex_for_providers(self, vertex_props: dict) -> tuple[bool, str]:
        """Validate that vertex properties are compatible with providers.

        Tests the vertex with actual providers to determine if any can handle it.
        """
        if not vertex_props:
            return False, "Empty vertex properties"

        if not self.providers:
            return False, "No providers available"

        from graphserver import Vertex

        vertex = Vertex(vertex_props)
        compatible_providers = []
        provider_results = []

        # Test vertex with each provider
        for provider_name, provider in self.providers.items():
            try:
                edges = list(provider(vertex))
                if edges:
                    compatible_providers.append(provider_name)
                    provider_results.append(f"{provider_name}: {len(edges)} edges")
                else:
                    provider_results.append(f"{provider_name}: no edges")
            except Exception as e:  # noqa: BLE001
                provider_results.append(f"{provider_name}: error ({str(e)[:50]}...)")

        if compatible_providers:
            return True, f"Compatible with: {', '.join(compatible_providers)}"
        return (
            False,
            f"No providers can handle this vertex. "
            f"Results: {'; '.join(provider_results)}",
        )
