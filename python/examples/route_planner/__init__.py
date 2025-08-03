"""Route Planner Example Application

An interactive web-based route planning application using the Graphserver engine.
Provides a map interface for selecting route endpoints and calculating paths.
"""

from .server import RoutePlannerServer

__version__ = "1.0.0"
__all__ = ["RoutePlannerServer"]
