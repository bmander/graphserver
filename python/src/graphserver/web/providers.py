"""Provider initialization and management for the graph web browser."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from graphserver import Engine

if TYPE_CHECKING:
    from graphserver.core import EdgeProvider


class ProviderError(Exception):
    """Raised when provider initialization fails."""

    pass


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
                raise ProviderError(
                    "No providers initialized. Please specify --osm or --gtfs files."
                )

            print(f"Initialized {len(self.providers)} provider(s)")
            return self.engine

        except Exception as e:
            raise ProviderError(f"Failed to initialize providers: {e}") from e

    def _initialize_transit_providers(self) -> None:
        """Initialize GTFS transit providers."""
        try:
            from graphserver.providers.transit import TransitProvider
        except ImportError as e:
            raise ProviderError(
                "Transit provider not available. Install with: "
                "pip install graphserver[transit]"
            ) from e

        for i, gtfs_file in enumerate(self.gtfs_files):
            gtfs_path = Path(gtfs_file)

            if not gtfs_path.exists():
                raise ProviderError(f"GTFS file not found: {gtfs_file}")

            if not (gtfs_path.is_file() and gtfs_path.suffix.lower() == ".zip"):
                raise ProviderError(f"GTFS file must be a .zip file: {gtfs_file}")

            try:
                # Create transit provider for this GTFS feed
                provider_name = f"transit_{i}" if i > 0 else "transit"
                transit_provider = TransitProvider(str(gtfs_path))

                self.providers[provider_name] = transit_provider
                self.engine.register_provider(provider_name, transit_provider)
                print(f"Registered transit provider: {gtfs_file}")

            except Exception as e:
                raise ProviderError(
                    f"Failed to initialize GTFS file {gtfs_file}: {e}"
                ) from e

    def _initialize_osm_providers(self) -> None:
        """Initialize OSM routing providers."""
        try:
            from graphserver.providers.osm import OSMNetworkProvider, OSMAccessProvider
        except ImportError as e:
            raise ProviderError(
                "OSM providers not available. Install with: "
                "pip install graphserver[osm]"
            ) from e

        # For now, use the first OSM file for the main providers
        # TODO: Support multiple OSM files in future
        osm_file = self.osm_files[0]
        osm_path = Path(osm_file)

        if not osm_path.exists():
            raise ProviderError(f"OSM file not found: {osm_file}")

        if not osm_path.is_file():
            raise ProviderError(f"OSM path must be a file: {osm_file}")

        try:
            # Create OSM network provider (handles osm_node_id vertices)
            osm_network = OSMNetworkProvider(str(osm_path))
            self.providers["osm_network"] = osm_network
            self.engine.register_provider("osm_network", osm_network)
            print(f"Registered OSM network provider: {osm_file}")

            # Create OSM access provider (handles lat/lon vertices)
            # This uses the same parser as the network provider for efficiency
            osm_access = OSMAccessProvider(parser=osm_network.parser)
            self.providers["osm_access"] = osm_access
            self.engine.register_provider("osm_access", osm_access)
            print(f"Registered OSM access provider: {osm_file}")

        except Exception as e:
            raise ProviderError(f"Failed to initialize OSM file {osm_file}: {e}") from e

        # Log additional OSM files that aren't yet supported
        if len(self.osm_files) > 1:
            print(f"Note: Multiple OSM files specified, but only using: {osm_file}")
            print("Multiple OSM file support will be added in a future version.")

        # Link transit stops to OSM network for cross-modal routing
        if self.gtfs_files and osm_access:
            self._link_transit_stops_to_osm(osm_access)

    def _link_transit_stops_to_osm(self, osm_access_provider) -> None:
        """Link all transit stops to nearby OSM nodes for multimodal routing.

        Args:
            osm_access_provider: The OSM access provider to use for linking
        """
        from graphserver import Vertex

        print("Linking transit stops to OSM network...")

        # Reset statistics
        self.linking_stats = {"total_stops": 0, "linked_stops": 0, "failed_links": []}

        # Find all transit providers
        transit_providers = {
            name: provider
            for name, provider in self.providers.items()
            if name.startswith("transit")
        }

        if not transit_providers:
            print("⚠️  No transit providers found for linking")
            return

        # Link stops from all transit providers
        for provider_name, transit_provider in transit_providers.items():
            if not hasattr(transit_provider, "parser") or not hasattr(
                transit_provider.parser, "stops"
            ):
                print(f"⚠️  Transit provider {provider_name} has no stops to link")
                continue

            provider_linked = 0
            provider_total = 0

            for stop in transit_provider.parser.stops.values():
                provider_total += 1
                self.linking_stats["total_stops"] += 1

                try:
                    # Create stop vertex for linking (using only stop_id, no coordinates)
                    stop_vertex = Vertex({"stop_id": stop.stop_id})

                    # Link to nearest OSM node using stop coordinates
                    osm_access_provider.link(stop_vertex, stop.lat, stop.lon)

                    provider_linked += 1
                    self.linking_stats["linked_stops"] += 1

                except ValueError as e:
                    # Stop too far from OSM network
                    error_msg = f"Stop {stop.stop_id}: {str(e)}"
                    self.linking_stats["failed_links"].append(error_msg)
                except Exception as e:
                    # Unexpected error
                    error_msg = f"Stop {stop.stop_id}: Unexpected error - {str(e)}"
                    self.linking_stats["failed_links"].append(error_msg)

            print(f"  {provider_name}: {provider_linked}/{provider_total} stops linked")

        # Print summary
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
            except Exception as e:
                provider_results.append(f"{provider_name}: error ({str(e)[:50]}...)")

        if compatible_providers:
            return True, f"Compatible with: {', '.join(compatible_providers)}"
        else:
            return (
                False,
                f"No providers can handle this vertex. Results: {'; '.join(provider_results)}",
            )
