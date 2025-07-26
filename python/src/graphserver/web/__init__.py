"""Graphserver Web Browser Module

A web-based interface for exploring graph vertices and edges through HTTP.
Provides a simple browser interface that accepts vertex properties as query
parameters and returns clickable links to adjacent vertices.
"""

from __future__ import annotations

from .server import GraphWebServer, main

__all__ = [
    "GraphWebServer",
    "main",
]
