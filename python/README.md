# Graphserver Python Package

Modern Python interface to the high-performance Graphserver planning engine.

## Features

- **High Performance**: C-based core engine optimized for speed
- **Python Flexibility**: Write edge providers in Python for maximum flexibility
- **Modern Python**: Full type hints, Python 3.12+ features
- **Memory Safe**: Automatic memory management across Python/C boundary

## Installation

### Development Installation

```bash
# Install in development mode
pip install -e ".[dev]"
```

### Requirements

- Python 3.12+
- CMake 3.15+
- C compiler supporting C99
- Core Graphserver library (built from ../core)

## Quick Start

```python
import graphserver

# Define an edge provider
def grid_provider(vertex):
    """Generate movement edges in a 2D grid"""
    x, y = vertex.get("x", 0), vertex.get("y", 0)
    edges = []
    
    # 4-directional movement
    for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        new_x, new_y = x + dx, y + dy
        if 0 <= new_x < 10 and 0 <= new_y < 10:  # 10x10 grid
            edges.append({
                "target": {"x": new_x, "y": new_y},
                "cost": 1.0
            })
    
    return edges

# Create engine and register provider
engine = graphserver.Engine()
engine.register_provider("grid", grid_provider)

# Plan a path
path = engine.plan(
    start={"x": 0, "y": 0},
    goal={"x": 9, "y": 9}
)

print(f"Path found: {len(path)} steps, cost: {path.total_cost}")
```

## Development

### Building

The package uses scikit-build-core for building the C extension:

```bash
# Build in place
python -m pip install -e .

# Build wheel
python -m build
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=graphserver

# Type checking
mypy src/

# Linting
ruff check src/ tests/
```

### Code Formatting

```bash
# Format code
black src/ tests/
ruff format src/ tests/
```

## Architecture

- **C Extension**: `_graphserver` module provides core functionality
- **Python Wrapper**: `graphserver.Engine` provides idiomatic Python API
- **Type Safety**: Full type annotations for IDE support and runtime checking
- **Memory Management**: Automatic cleanup using Python's garbage collection

## License

This package is part of the Graphserver project.