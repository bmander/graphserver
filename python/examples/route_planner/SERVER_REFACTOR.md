# Route Planner Server Refactor Plan

This plan improves clarity, conciseness, and maintainability of `python/examples/route_planner/server.py` without changing external behavior or API endpoints.

## Objectives
- Reduce file size by separating concerns into focused modules.
- Make HTTP routing and error handling consistent and easy to scan.
- Remove hidden global state on the handler class; use explicit dependency wiring.
- Centralize common helpers (JSON I/O, validation, responses).
- Keep route geometry generation lean; gate heavy metrics behind a flag.
- Improve safety (static path handling) and observability (structured logging).

## Non‑Goals
- Changing public endpoints (`/`, `/api/status`, `/api/bounds`, `/api/providers`, `/api/route`).
- Changing the route planning algorithm or providers’ behavior.
- Adding new features beyond small developer‑centric improvements (logging, flags).

## Current Pain Points
- One large file mixes HTTP serving, routing utilities, I/O, and bootstrapping.
- Handler stores shared state via class attributes (implicit globals), obscuring dependencies.
- Repeated patterns for JSON responses, input parsing, and validation.
- Verbose `if/elif` chains for routing; inconsistent API error format (`send_error` vs JSON).
- Inner imports and repeated metadata checks in hot paths.
- Static file path check relies on string `startswith`.

## Target Architecture
- `server.py` (runner)
  - `RoutePlannerServer` bootstrapping, CLI entry, and startup logs.
  - `make_handler(engine, providers, osm_data, server_config)` factory returning a bound `BaseHTTPRequestHandler` subclass.
- `handler.py` (HTTP layer)
  - `RoutePlannerHandler` subclass using a small route dispatch map per method.
  - Thin handlers delegating to helpers/utilities; unified JSON responses/errors.
- `routing_utils.py` (routing utilities)
  - `encode_polyline`, `extract_way_segment_coordinates`, `path_result_to_geojson(debug_metrics: bool = False)`.
  - Consolidated metadata access and optional metrics computation.
- `web_utils.py` (HTTP helpers)
  - `json_response`, `json_error`, `parse_json`, `validate_point`, static file serving helper.
- `types.py` (optional)
  - `Coord = TypedDict("Coord", {"lat": float, "lng": float})` and small aliases for clarity.
- `constants.py` (optional)
  - `DEFAULT_BOUNDS`, common headers like `NO_CACHE_HEADERS`.

## API & Behavior Compatibility
- Endpoints and payload shapes unchanged.
- Static files continue to serve from `static/` relative to module directory.
- Error responses for `/api/*` consistently return JSON (HTTP 200 with `status: error`) as today’s code often does.

## Refactor Steps
1) Introduce logging
- Add `logging` setup in `server.py`; use `logger = logging.getLogger(__name__)` in modules.
- Replace `print` in libraries with `logger.info/debug/warning/error` (keep concise startup prints in `RoutePlannerServer.run()`).

2) Extract HTTP helpers
- Create `web_utils.py` with `json_response`, `json_error`, `parse_json`, `validate_point` to remove duplication in the handler.
- Centralize cache headers and content length handling.

3) Tighten routing utilities
- Move `encode_polyline`, `extract_way_segment_coordinates`, and `path_result_to_geojson` to `routing_utils.py`.
- In `path_result_to_geojson`:
  - Remove unused `enumerate` and duplicate `hasattr` checks by caching `metadata` once.
  - Add `debug_metrics: bool = False` parameter; compute sizes/timing only when enabled.
  - Keep coordinate order `[lng, lat]` and standardize naming (`lng` consistently).

4) Safer static file serving
- Replace `startswith` path check with `Path.is_relative_to(base)` when available; fallback to manual resolution check.
- Optionally consider `SimpleHTTPRequestHandler` for static assets; keep custom API handling.

5) Replace handler class globals with factory
- Implement `make_handler(engine, providers, osm_data, server_config)` that closes over dependencies and returns a handler subclass.
- Remove `RoutePlannerHandler.engine/providers/osm_data` attribute mutation.

6) Route dispatch map
- Replace `if/elif` chains with per‑method dispatch dicts:
  - `GET`: `/`, `/api/status`, `/api/bounds`, `/api/providers`, static files prefix.
  - `POST`: `/api/route`.
- Keep a simple prefix handler for `/static/`.

7) Consolidate validation
- Use `validate_point` to coerce and validate `origin`/`destination`.
- Keep `_approx_distance_km(origin, destination)` as a small helper.

8) Imports & typing cleanup
- Move inner imports (`json`, `time`, `math`) to module scope.
- Add `TypedDict` for coordinates and type aliases for GeoJSON dicts.

9) Documentation & examples
- Update `README.md` snippets if they reference `server.py` directly.
- Ensure `__main__.py` or Makefile entry points still work (import path updates).

## Testing & Verification
- Unit checks:
  - `encode_polyline` round‑trip with a small coordinate set.
  - `extract_way_segment_coordinates` with mocked `OSMDataSource`/way/node structures.
  - `path_result_to_geojson` with a minimal fake `PathResult` and `edge.metadata` presence/absence.
- Integration checks:
  - Start server; verify `GET /`, `GET /api/status`, `GET /api/bounds`, `GET /api/providers`.
  - POST `/api/route` with nearby points; assert success payload with `encoded_polyline`.
  - Invalid payloads return structured JSON errors.

## Rollout & Flags
- Add env/config flag `ROUTE_DEBUG_METRICS` to toggle metrics computation in `path_result_to_geojson`.
- Default OFF to minimize overhead and response size.

## Risks & Mitigations
- Dependency wiring: ensure handler factory passes `engine/providers/osm_data`; add clear error when missing.
- Static path logic: thoroughly test relative/absolute paths, directory traversal attempts.
- Logging verbosity: set sensible defaults; keep emojis only in CLI startup prints.

## Work Items Checklist
- [x] Add logging and configure levels.
- [x] Add `web_utils.py` with HTTP helpers.
- [ ] Create `routing_utils.py` and move routing helpers.
- [ ] Add optional `types.py` and `constants.py`.
- [ ] Implement handler factory; remove class attribute globals.
- [ ] Introduce route dispatch maps in handler.
- [ ] Replace static path guard with `is_relative_to` fallback.
- [ ] Wire up `ROUTE_DEBUG_METRICS` and plumb into `path_result_to_geojson`.
- [ ] Update imports and run integration checks.
- [ ] Refresh README/Makefile references if needed.

