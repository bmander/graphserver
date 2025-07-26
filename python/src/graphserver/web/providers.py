"""Provider initialization and management for the graph web browser."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from graphserver import Engine
from graphserver.core import EdgeProvider


class ProviderError(Exception):
    """Raised when provider initialization fails."""
    pass


class ProviderManager:
    """Manages provider initialization and engine configuration."""

    def __init__(self, osm_files: Sequence[str] | None = None,
                 gtfs_files: Sequence[str] | None = None):
        self.osm_files = list(osm_files or [])
        self.gtfs_files = list(gtfs_files or [])
        self.engine: Engine | None = None
        self.providers: dict[str, EdgeProvider] = {}

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
            
            if not (gtfs_path.is_file() and gtfs_path.suffix.lower() == '.zip'):
                raise ProviderError(
                    f"GTFS file must be a .zip file: {gtfs_file}"
                )

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
            from graphserver.providers.osm import (
                OSMNetworkProvider, 
                OSMAccessProvider
            )
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
            raise ProviderError(
                f"Failed to initialize OSM file {osm_file}: {e}"
            ) from e

        # Log additional OSM files that aren't yet supported
        if len(self.osm_files) > 1:
            print(f"Note: Multiple OSM files specified, but only using: {osm_file}")
            print("Multiple OSM file support will be added in a future version.")

    def get_provider_info(self) -> dict[str, str]:
        """Get information about initialized providers for display."""
        info = {}
        
        if self.osm_files:
            info["OSM"] = f"{len(self.osm_files)} file(s): {', '.join(self.osm_files)}"
            
        if self.gtfs_files:
            info["GTFS"] = f"{len(self.gtfs_files)} file(s): {', '.join(self.gtfs_files)}"
            
        return info

    def validate_vertex_for_providers(self, vertex_props: dict) -> tuple[bool, str]:
        """Validate that vertex properties are compatible with providers."""
        if not vertex_props:
            return False, "Empty vertex properties"

        # Check for supported vertex patterns
        supported_patterns = []
        
        if "osm_network" in self.providers:
            supported_patterns.append("osm_node_id (integer)")
            
        if "osm_access" in self.providers:
            supported_patterns.append("lat, lon (floats)")
            
        if any(name.startswith("transit") for name in self.providers):
            supported_patterns.extend([
                "lat, lon, time (floats, integer)",
                "stop_id, time (string, integer)"
            ])

        # Check if vertex matches any supported pattern
        has_osm_node = "osm_node_id" in vertex_props
        has_coords = "lat" in vertex_props and "lon" in vertex_props
        has_time = "time" in vertex_props
        has_stop = "stop_id" in vertex_props

        valid_patterns = []
        
        if has_osm_node and "osm_network" in self.providers:
            valid_patterns.append("OSM node routing")
            
        if has_coords and "osm_access" in self.providers:
            valid_patterns.append("coordinate-based routing")
            
        if has_coords and has_time and any(name.startswith("transit") 
                                           for name in self.providers):
            valid_patterns.append("transit routing from coordinates")
            
        if has_stop and has_time and any(name.startswith("transit") 
                                         for name in self.providers):
            valid_patterns.append("transit routing from stop")

        if valid_patterns:
            return True, f"Compatible with: {', '.join(valid_patterns)}"
        else:
            return False, (
                f"Vertex properties don't match any provider patterns. "
                f"Supported: {', '.join(supported_patterns)}"
            )