"""Provider initialization and management for the graph web browser."""
# ruff: noqa: T201

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from graphserver import Engine, GraphserverDataType

if TYPE_CHECKING:
    from graphserver.core import EdgeProvider
    from graphserver.providers.osm.access_provider import OSMAccessProvider
    from graphserver.providers.transit.provider import TransitProvider
    from graphserver.providers.transit.types import Stop


@dataclass
class LinkingStats:
    """Cross-modal linking statistics."""

    total_stops: int = 0
    linked_stops: int = 0
    failed_links: list[str] = field(default_factory=list)


@dataclass
class GTFSFeedStats:
    """Statistics for a GTFS feed."""

    stops: int
    routes: int
    trips: int


@dataclass
class OSMProviderStats:
    """Statistics for OSM provider data."""

    nodes: int
    ways: int
    edges: int


# Type alias for progress callback function
ProgressCallback = Callable[[str, int, int], None] | None
# Arguments: (description, current_step, total_steps)


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
        self.linking_stats = LinkingStats()

    def initialize_engine(self, progress_callback: ProgressCallback = None) -> Engine:
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
                self._initialize_transit_providers(progress_callback)

            # Initialize OSM providers if OSM files specified
            if self.osm_files:
                self._initialize_osm_providers(progress_callback)

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

        # tqdm dependency removed - progress bars handled at CLI layer

    # _create_progress_callback method removed - using direct callbacks now

    def _validate_gtfs_file(self, gtfs_path: Path) -> None:
        """Validate that GTFS file exists and is a valid zip file."""
        if not gtfs_path.exists():
            msg = f"GTFS file not found: {gtfs_path}"
            raise ProviderError(msg)

        if not (gtfs_path.is_file() and gtfs_path.suffix.lower() == ".zip"):
            msg = f"GTFS file must be a .zip file: {gtfs_path}"
            raise ProviderError(msg)

    def _register_transit_provider(
        self,
        transit_provider: TransitProvider,
        provider_name: str,
        progress_callback: ProgressCallback = None,
    ) -> GTFSFeedStats:
        """Register transit provider and collect statistics."""
        assert (
            self.engine is not None
        )  # Engine must be initialized before registering providers

        if progress_callback:
            progress_callback("Registering provider...", 0, 1)

        self.providers[provider_name] = transit_provider
        self.engine.register_provider(provider_name, transit_provider)

        # Collect statistics for this feed
        feed_stops = transit_provider.parser.stop_count
        feed_routes = transit_provider.parser.route_count
        feed_trips = transit_provider.parser.trip_count

        if progress_callback:
            progress_callback(
                f"stops: {feed_stops}, routes: {feed_routes}, trips: {feed_trips}", 1, 1
            )

        return GTFSFeedStats(stops=feed_stops, routes=feed_routes, trips=feed_trips)

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

        # tqdm dependency removed - progress bars handled at CLI layer

    def _validate_osm_file(self, osm_path: Path) -> None:
        """Validate that OSM file exists and is a valid file."""
        if not osm_path.exists():
            msg = f"OSM file not found: {osm_path}"
            raise ProviderError(msg)

        if not osm_path.is_file():
            msg = f"OSM path must be a file: {osm_path}"
            raise ProviderError(msg)

    def _install_osm_providers(
        self, osm_path: Path, progress_callback: ProgressCallback = None
    ) -> tuple[OSMAccessProvider, OSMProviderStats]:
        """Create and install OSM providers and return statistics.

        Registers both OSM network and access providers; returns the access provider."""

        from graphserver.providers.osm import (
            OSMAccessProvider,
            OSMDataSource,
            OSMNetworkProvider,
        )

        # Get file size for context
        file_size_mb = osm_path.stat().st_size / (1024 * 1024)
        size_info = f"{file_size_mb:.1f}MB"

        # Step 1: Create OSM data source
        if progress_callback:
            progress_callback(
                f"Parsing OSM file ({osm_path.name}, {size_info})...", 0, 4
            )
        osm_data = OSMDataSource(osm_path)

        # Step 2: Show parsing results
        raw_nodes = osm_data.node_count
        raw_ways = osm_data.way_count
        raw_edges = osm_data.edge_count
        if progress_callback:
            progress_callback(
                f"Parsed: {raw_nodes} nodes, {raw_ways} ways, {raw_edges} edges", 1, 4
            )

        # Step 3: Create OSM network provider (handles osm_node_id vertices)
        if progress_callback:
            progress_callback("Creating network provider...", 2, 4)
        osm_network = OSMNetworkProvider(osm_data)
        self.providers["osm_network"] = osm_network
        assert (
            self.engine is not None
        )  # Engine must be initialized before registering providers
        self.engine.register_provider("osm_network", osm_network)

        # Step 4: Create OSM access provider (handles lat/lon vertices)
        if progress_callback:
            progress_callback("Creating access provider...", 3, 4)
        osm_access = OSMAccessProvider(osm_data)
        self.providers["osm_access"] = osm_access
        assert (
            self.engine is not None
        )  # Engine must be initialized before registering providers
        self.engine.register_provider("osm_access", osm_access)

        if progress_callback:
            progress_callback("OSM providers complete", 4, 4)

        return osm_access, OSMProviderStats(
            nodes=raw_nodes, ways=raw_ways, edges=raw_edges
        )

    def _print_osm_summary(self, stats: OSMProviderStats, osm_path: Path) -> None:
        """Print summary of loaded OSM providers."""
        print(
            f"✅ Registered OSM providers: {stats.nodes} nodes, "
            f"{stats.ways} ways, {stats.edges} edges ({osm_path.name})"
        )

    def _process_single_gtfs_file(
        self, i: int, gtfs_file: str, progress_callback: ProgressCallback = None
    ) -> GTFSFeedStats:
        """Process a single GTFS file and return statistics."""
        from graphserver.providers.transit import TransitProvider

        gtfs_path = Path(gtfs_file)
        if progress_callback:
            progress_callback(f"Loading GTFS ({gtfs_path.name})", 0, 10)

        self._validate_gtfs_file(gtfs_path)

        try:
            # Parse GTFS data with detailed progress
            provider_name = f"transit_{i}" if i > 0 else "transit"

            # Create a sub-progress callback for the TransitProvider
            def transit_progress_callback(
                step_name: str,
                current: int,
                total: int,
                sub_progress: float | None = None,  # noqa: ARG001
            ) -> None:
                if progress_callback:
                    # Map the 9 parsing steps to our progress (steps 1-9 out of 10)
                    mapped_current = current + 1  # offset by 1 since we start at step 0
                    progress_callback(step_name, mapped_current, 10)

            transit_provider = TransitProvider(
                str(gtfs_path), progress_callback=transit_progress_callback
            )

            # Register provider and collect statistics (step 10)
            return self._register_transit_provider(
                transit_provider, provider_name, progress_callback
            )

        except Exception as e:
            msg = f"Failed to initialize GTFS file {gtfs_file}: {e}"
            raise ProviderError(msg) from e

    def _initialize_transit_providers(
        self, progress_callback: ProgressCallback = None
    ) -> None:
        """Initialize GTFS transit providers."""
        self._validate_transit_imports()

        # Initialize progress tracking for GTFS loading (10 steps per file)
        total_steps = len(self.gtfs_files) * 10  # 9 parsing steps + 1 register step
        total_stops = 0
        total_routes = 0
        total_trips = 0
        current_step = 0

        for i, gtfs_file in enumerate(self.gtfs_files):
            # Create a progress callback for this file that maps to overall progress
            def file_progress_callback(
                description: str,
                file_current: int,
                file_total: int,  # noqa: ARG001
            ) -> None:
                if progress_callback:
                    overall_current = current_step + file_current
                    progress_callback(description, overall_current, total_steps)

            feed_stats = self._process_single_gtfs_file(
                i, gtfs_file, file_progress_callback
            )
            total_stops += feed_stats.stops
            total_routes += feed_stats.routes
            total_trips += feed_stats.trips
            current_step += 10  # Move to next file's steps

        if progress_callback:
            progress_callback("GTFS loading complete", total_steps, total_steps)

        # Print detailed summary
        self._print_transit_summary(total_stops, total_routes, total_trips)

    def _initialize_osm_providers(
        self, progress_callback: ProgressCallback = None
    ) -> None:
        """Initialize OSM routing providers."""
        self._validate_osm_imports()

        # For now, use the first OSM file for the main providers
        # Multiple OSM file support tracked in: https://github.com/bmander/graphserver/issues/50
        osm_file = self.osm_files[0]
        osm_path = Path(osm_file)

        self._validate_osm_file(osm_path)

        try:
            osm_access, stats = self._install_osm_providers(osm_path, progress_callback)
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
            self._link_transit_stops_to_osm(osm_access, progress_callback)

    def _get_transit_providers_for_linking(self) -> dict[str, TransitProvider]:
        """Get transit providers that have stops available for linking."""
        from graphserver.providers.transit import TransitProvider

        transit_providers = {
            name: provider
            for name, provider in self.providers.items()
            if name.startswith("transit") and isinstance(provider, TransitProvider)
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

    def _link_single_stop(
        self, stop: Stop, osm_access_provider: OSMAccessProvider
    ) -> tuple[bool, str | None]:
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
        total_stops = self.linking_stats.total_stops
        linked_stops = self.linking_stats.linked_stops
        failed_links = self.linking_stats.failed_links
        failed_count = len(failed_links)

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
                    for error in failed_links:
                        print(f"     {error}")
                else:
                    for error in failed_links[:3]:
                        print(f"     {error}")
                    print(f"     ... and {failed_count - 3} more")
        else:
            print("⚠️  No transit stops found to link")

    def _link_transit_stops_to_osm(
        self,
        osm_access_provider: OSMAccessProvider,
        progress_callback: ProgressCallback = None,
    ) -> None:
        """Link all transit stops to nearby OSM nodes for multimodal routing.

        Args:
            osm_access_provider: The OSM access provider to use for linking
        """
        # Reset statistics
        self.linking_stats = LinkingStats()

        # Get valid transit providers
        transit_providers = self._get_transit_providers_for_linking()
        if not transit_providers:
            return

        # Count total stops for progress tracking
        total_stops = sum(
            len(provider.parser.stops) for provider in transit_providers.values()
        )

        current_stop = 0

        # Link stops from all transit providers
        for provider_name, transit_provider in transit_providers.items():
            provider_linked = 0
            provider_total = 0

            for stop in transit_provider.parser.stops.values():
                provider_total += 1
                self.linking_stats.total_stops += 1

                if progress_callback:
                    progress_callback(
                        f"Linking stop {stop.stop_id}", current_stop, total_stops
                    )

                success, error_msg = self._link_single_stop(stop, osm_access_provider)
                if success:
                    provider_linked += 1
                    self.linking_stats.linked_stops += 1
                elif error_msg is not None:
                    self.linking_stats.failed_links.append(error_msg)

                current_stop += 1

            if progress_callback:
                progress_callback(
                    f"Linked {provider_name}: {provider_linked}/{provider_total}",
                    current_stop,
                    total_stops,
                )

        if progress_callback:
            progress_callback("Transit stop linking complete", total_stops, total_stops)

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
        if self.osm_files and self.gtfs_files and self.linking_stats.total_stops > 0:
            linked_stops = self.linking_stats.linked_stops
            total_stops = self.linking_stats.total_stops
            success_rate = (linked_stops / total_stops) * 100 if total_stops > 0 else 0
            info["Cross-modal links"] = (
                f"{linked_stops}/{total_stops} transit stops linked to OSM network "
                f"({success_rate:.1f}%)"
            )

        return info

    def validate_vertex_for_providers(
        self, vertex_props: dict[str, GraphserverDataType]
    ) -> tuple[bool, str]:
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
