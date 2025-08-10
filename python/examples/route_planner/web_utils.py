"""HTTP utility functions for the route planner web application."""

import json
import logging
from http.server import BaseHTTPRequestHandler
from typing import Any

logger = logging.getLogger(__name__)

# Coordinate validation constants
MIN_LATITUDE = -90
MAX_LATITUDE = 90
MIN_LONGITUDE = -180
MAX_LONGITUDE = 180

# Common HTTP headers
NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}

JSON_HEADERS = {
    "Content-Type": "application/json",
    **NO_CACHE_HEADERS,
}


def send_json_response(
    handler: BaseHTTPRequestHandler, data: dict[str, Any], status: int = 200
) -> None:
    """Send a JSON response with proper headers.

    Args:
        handler: HTTP request handler
        data: Data to serialize as JSON
        status: HTTP status code (default: 200)
    """
    try:
        response_body = json.dumps(data, indent=2).encode("utf-8")

        handler.send_response(status)
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(response_body)))
        for header, value in NO_CACHE_HEADERS.items():
            handler.send_header(header, value)
        handler.end_headers()

        handler.wfile.write(response_body)
    except (TypeError, ValueError):
        logger.exception("Error serializing JSON response")
        send_http_error(handler, 500, "Error serializing JSON")


def send_json_error(
    handler: BaseHTTPRequestHandler,
    status: int,
    error_message: str,
    error_code: str | None = None,
    error_details: str | None = None,
    debug_info: dict[str, Any] | None = None,
) -> None:
    """Send a structured JSON error response.

    Args:
        handler: HTTP request handler
        status: HTTP status code
        error_message: Human-readable error message
        error_code: Machine-readable error code
        error_details: Detailed error description
        debug_info: Debug information dictionary
    """
    properties: dict[str, Any] = {
        "status": "error",
        "error": error_message,
        "total_cost": 0,
    }

    if error_code:
        properties["error_code"] = error_code
    if error_details:
        properties["error_details"] = error_details
    if debug_info:
        properties["debug_info"] = debug_info

    response = {
        "type": "FeatureCollection",
        "features": [],
        "properties": properties,
    }

    # For API errors, send as HTTP 200 with error status in JSON
    # This matches the existing behavior
    send_json_response(handler, response, status=200)


def send_http_error(handler: BaseHTTPRequestHandler, status: int, message: str) -> None:
    """Send a standard HTTP error response.

    Args:
        handler: HTTP request handler
        status: HTTP status code
        message: Error message
    """
    handler.send_error(status, message)


def parse_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
    """Parse JSON from request body with error handling.

    Args:
        handler: HTTP request handler

    Returns:
        Parsed JSON data or None if parsing failed
    """
    content_length = int(handler.headers.get("Content-Length", 0))
    if content_length == 0:
        send_http_error(handler, 400, "Empty request body")
        return None

    try:
        post_data = handler.rfile.read(content_length)
        result: dict[str, Any] = json.loads(post_data.decode("utf-8"))
        return result  # noqa: TRY300
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        send_http_error(handler, 400, f"Invalid JSON: {e}")
        return None


def validate_point(point: Any, point_name: str) -> dict[str, float] | None:
    """Validate and normalize a coordinate point.

    Args:
        point: Point data to validate
        point_name: Name of the point (for error messages)

    Returns:
        Validated point with lat/lng as floats, or None if invalid
    """
    if not isinstance(point, dict) or "lat" not in point or "lng" not in point:
        return None

    try:
        lat = float(point["lat"])
        lng = float(point["lng"])

        # Basic coordinate validation
        if not (MIN_LATITUDE <= lat <= MAX_LATITUDE):
            return None
        if not (MIN_LONGITUDE <= lng <= MAX_LONGITUDE):
            return None

        return {"lat": lat, "lng": lng}  # noqa: TRY300
    except (ValueError, TypeError):
        return None


def validate_request_fields(
    data: dict[str, Any], required_fields: list[str]
) -> list[str]:
    """Check for required fields in request data.

    Args:
        data: Request data dictionary
        required_fields: List of required field names

    Returns:
        List of missing field names (empty if all present)
    """
    return [field for field in required_fields if field not in data]


def add_no_cache_headers(handler: BaseHTTPRequestHandler) -> None:
    """Add no-cache headers to the response.

    Args:
        handler: HTTP request handler
    """
    for header, value in NO_CACHE_HEADERS.items():
        handler.send_header(header, value)
