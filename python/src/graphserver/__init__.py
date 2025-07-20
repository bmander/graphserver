"""Graphserver Planning Engine Python Package

A modern Python interface to the high-performance Graphserver planning engine.
Supports dynamic edge providers written in Python for flexible pathfinding
across various domains.
"""

from __future__ import annotations

from .core import Engine, PathResult, EdgeProvider

__version__ = "2.0.0"
__all__ = ["Engine", "PathResult", "EdgeProvider"]