from typing import Any

__version__: str

def create_engine(config: dict[str, Any] | None = None) -> Any: ...
def register_provider(engine: Any, name: str, provider: Any) -> None: ...
def plan(
    engine: Any, start_vertex_data: dict[str, Any], end_vertex_data: dict[str, Any]
) -> dict[str, Any]: ...
def get_engine_stats(engine: Any) -> dict[str, int]: ...
def precache_subgraph(
    engine: Any,
    provider_name: str,
    vertex_data: dict[str, Any],
    radius: int,
    max_vertices: int,
) -> None: ...
