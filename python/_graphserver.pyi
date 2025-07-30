from collections.abc import Sequence
from typing import Any

__version__: str

def create_engine(*, enable_edge_caching: bool = False) -> Any: ...
def register_provider(engine: Any, name: str, provider: Any) -> None: ...
def plan(
    engine: Any,
    start_vertex_data: dict[str, Any],
    end_vertex_data: dict[str, Any],
    planner: Any,
) -> Sequence[dict[str, Any]]: ...
def get_engine_stats(engine: Any) -> dict[str, int]: ...
def precache_subgraph(
    *,
    engine: Any,
    provider_name: str,
    seed_vertices: list[dict[str, Any]],
    max_depth: int,
    max_vertices: int,
) -> None: ...
