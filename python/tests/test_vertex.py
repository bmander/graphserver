"""Tests for immutable Vertex class functionality.

This module contains comprehensive tests for the immutable Vertex class,
including creation, hash functionality, equality, and immutability enforcement.
"""

from __future__ import annotations

import pytest

from graphserver import Vertex


class TestVertexCreation:
    """Test vertex creation and initialization."""

    def test_vertex_creation_empty(self) -> None:
        """Test creating empty vertices."""
        vertex = Vertex()
        assert len(vertex.keys()) == 0
        assert vertex.to_dict() == {}

    def test_vertex_creation_with_data(self) -> None:
        """Test creating vertices with initial data."""
        data = {"x": 10, "y": 20, "name": "test"}
        vertex = Vertex(data)

        assert vertex["x"] == 10
        assert vertex["y"] == 20
        assert vertex["name"] == "test"
        assert len(vertex.keys()) == 3

    def test_vertex_creation_with_custom_hash(self) -> None:
        """Test creating vertices with custom hash values."""
        data = {"x": 10, "y": 20}
        custom_hash = 12345
        vertex = Vertex(data, hash_value=custom_hash)

        assert vertex["x"] == 10
        assert vertex["y"] == 20
        assert hash(vertex) == custom_hash

        # to_dict should include the hash
        vertex_dict = vertex.to_dict()
        assert vertex_dict["_hash"] == custom_hash

    def test_vertex_creation_with_hash_in_data(self) -> None:
        """Test creating vertices when data contains _hash key."""
        data = {"x": 10, "y": 20, "_hash": 54321}
        vertex = Vertex(data)

        # Hash should be extracted from data
        assert vertex["x"] == 10
        assert vertex["y"] == 20
        assert "_hash" not in vertex  # Should be removed from data
        assert hash(vertex) == 54321

    def test_explicit_hash_overrides_data_hash(self) -> None:
        """Test that explicit hash_value parameter overrides _hash in data."""
        data = {"x": 10, "y": 20, "_hash": 54321}
        explicit_hash = 99999
        vertex = Vertex(data, hash_value=explicit_hash)

        # Explicit hash should take precedence
        assert hash(vertex) == explicit_hash
        assert vertex.to_dict()["_hash"] == explicit_hash


class TestVertexImmutability:
    """Test vertex immutability enforcement."""

    def test_vertex_immutability(self) -> None:
        """Test that vertex mutation attempts raise TypeError."""
        vertex = Vertex({"x": 10, "y": 20})

        # Attempting to set an item should raise TypeError
        with pytest.raises(TypeError, match="Vertex objects are immutable"):
            vertex["z"] = 30

        # Original data should be unchanged
        assert "z" not in vertex
        assert vertex["x"] == 10
        assert vertex["y"] == 20

    def test_vertex_data_isolation(self) -> None:
        """Test that original data dict cannot be used to mutate vertex."""
        original_data = {"x": 10, "y": 20}
        vertex = Vertex(original_data)

        # Modifying original data should not affect vertex
        original_data["z"] = 30
        assert "z" not in vertex
        assert len(vertex.keys()) == 2


class TestVertexHashFunctionality:
    """Test vertex hash computation and behavior."""

    def test_vertex_hash_consistency(self) -> None:
        """Test that vertices with same data have same hash."""
        vertex1 = Vertex({"x": 10, "y": 20})
        vertex2 = Vertex({"x": 10, "y": 20})

        assert hash(vertex1) == hash(vertex2)

    def test_vertex_hash_differs_for_different_data(self) -> None:
        """Test that vertices with different data have different hashes."""
        vertex1 = Vertex({"x": 10, "y": 20})
        vertex2 = Vertex({"x": 10, "y": 30})

        assert hash(vertex1) != hash(vertex2)

    def test_custom_hash_functionality(self) -> None:
        """Test custom hash parameter functionality."""
        data = {"x": 10, "y": 20}
        custom_hash = 12345
        vertex = Vertex(data, hash_value=custom_hash)

        # Should use custom hash
        assert hash(vertex) == custom_hash

        # Different vertex with same data should have different hash by default
        vertex_default = Vertex(data)
        assert hash(vertex_default) != custom_hash

    def test_hash_roundtrip_preservation(self) -> None:
        """Test that hash values survive to_dict/from_dict roundtrip."""
        original_data = {"x": 10, "y": 20}
        custom_hash = 99999
        original_vertex = Vertex(original_data, hash_value=custom_hash)

        # Convert to dict and back
        vertex_dict = original_vertex.to_dict()
        reconstructed_vertex = Vertex(vertex_dict)

        # Hash should be preserved
        assert hash(original_vertex) == hash(reconstructed_vertex)
        assert hash(reconstructed_vertex) == custom_hash


class TestVertexEquality:
    """Test vertex equality behavior."""

    def test_vertex_equality_same_data(self) -> None:
        """Test that vertices with same data are equal."""
        vertex1 = Vertex({"x": 10, "y": 20})
        vertex2 = Vertex({"x": 10, "y": 20})

        assert vertex1 == vertex2
        assert vertex2 == vertex1

    def test_vertex_equality_different_data(self) -> None:
        """Test that vertices with different data are not equal."""
        vertex1 = Vertex({"x": 10, "y": 20})
        vertex2 = Vertex({"x": 10, "y": 30})

        assert vertex1 != vertex2
        assert vertex2 != vertex1

    def test_vertex_equality_with_custom_hash(self) -> None:
        """Test equality behavior with custom hashes."""
        data = {"x": 10, "y": 20}
        vertex1 = Vertex(data, hash_value=1111)
        vertex2 = Vertex(data, hash_value=2222)
        vertex3 = Vertex(data)  # Default hash

        # Equality should be based on data, not hash
        assert vertex1 == vertex2
        assert vertex1 == vertex3
        assert vertex2 == vertex3

        # But hashes should be different
        assert hash(vertex1) != hash(vertex2)
        assert hash(vertex1) != hash(vertex3)

    def test_vertex_inequality_with_other_types(self) -> None:
        """Test vertex inequality with non-vertex objects."""
        vertex = Vertex({"x": 10})

        assert vertex != {"x": 10}
        assert vertex != "not a vertex"
        assert vertex != 42
        assert vertex is not None


class TestVertexDictionaryInterface:
    """Test vertex dictionary-like interface."""

    def test_vertex_getitem(self) -> None:
        """Test vertex item access."""
        vertex = Vertex({"x": 10, "y": 20.5, "name": "test", "active": True})

        assert vertex["x"] == 10
        assert vertex["y"] == 20.5
        assert vertex["name"] == "test"
        assert vertex["active"] is True

    def test_vertex_getitem_keyerror(self) -> None:
        """Test that accessing non-existent key raises KeyError."""
        vertex = Vertex({"x": 10})

        with pytest.raises(KeyError):
            _ = vertex["nonexistent"]

    def test_vertex_contains(self) -> None:
        """Test vertex key membership testing."""
        vertex = Vertex({"x": 10, "y": 20})

        assert "x" in vertex
        assert "y" in vertex
        assert "z" not in vertex

    def test_vertex_keys(self) -> None:
        """Test vertex keys() method."""
        data = {"x": 10, "y": 20, "name": "test"}
        vertex = Vertex(data)

        keys = vertex.keys()
        assert set(keys) == {"x", "y", "name"}

    def test_vertex_values_via_items(self) -> None:
        """Test getting vertex values via items() method."""
        data = {"x": 10, "y": 20, "name": "test"}
        vertex = Vertex(data)

        # Get values through items since values() method doesn't exist
        values = [value for key, value in vertex.items()]
        assert set(values) == {10, 20, "test"}

    def test_vertex_items(self) -> None:
        """Test vertex items() method."""
        data = {"x": 10, "y": 20, "name": "test"}
        vertex = Vertex(data)

        items = dict(vertex.items())
        assert items == data

    def test_vertex_get_method(self) -> None:
        """Test vertex get() method."""
        vertex = Vertex({"x": 10, "y": 20})

        assert vertex.get("x") == 10
        assert vertex.get("z") is None
        assert vertex.get("z", "default") == "default"


class TestVertexToDictMethod:
    """Test vertex to_dict() method."""

    def test_to_dict_basic(self) -> None:
        """Test basic to_dict functionality."""
        data = {"x": 10, "y": 20, "name": "test"}
        vertex = Vertex(data)

        result = vertex.to_dict()
        assert isinstance(result, dict)
        # Should not include _hash for vertices without custom hash
        assert set(result.keys()) == {"x", "y", "name"}
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["name"] == "test"

    def test_to_dict_with_custom_hash(self) -> None:
        """Test to_dict includes custom hash."""
        data = {"x": 10, "y": 20}
        custom_hash = 12345
        vertex = Vertex(data, hash_value=custom_hash)

        result = vertex.to_dict()
        assert result["x"] == 10
        assert result["y"] == 20
        assert result["_hash"] == custom_hash

    def test_to_dict_returns_copy(self) -> None:
        """Test that to_dict returns a copy that can be modified."""
        vertex = Vertex({"x": 10, "y": 20})

        result = vertex.to_dict()
        result["z"] = 30  # Should not affect original vertex

        assert "z" not in vertex
        assert vertex.get("z") is None


class TestVertexStringRepresentation:
    """Test vertex string representation."""

    def test_vertex_repr(self) -> None:
        """Test vertex __repr__ method."""
        data = {"x": 10, "y": 20}
        vertex = Vertex(data)

        repr_str = repr(vertex)
        assert repr_str == "Vertex({'x': 10, 'y': 20})"

    def test_vertex_repr_empty(self) -> None:
        """Test repr of empty vertex."""
        vertex = Vertex()

        repr_str = repr(vertex)
        assert repr_str == "Vertex({})"


class TestVertexEdgeCases:
    """Test vertex edge cases and complex scenarios."""

    def test_vertex_with_none_values(self) -> None:
        """Test vertex with None values."""
        vertex = Vertex({"x": None, "y": 10})

        assert vertex["x"] is None
        assert vertex["y"] == 10
        assert "x" in vertex

    def test_vertex_with_complex_data_types(self) -> None:
        """Test vertex with various data types."""
        data = {
            "int_val": 42,
            "float_val": 3.14,
            "str_val": "hello",
            "bool_val": True,
            "list_val": [1, 2, 3],
            "none_val": None,
        }
        vertex = Vertex(data)

        assert vertex["int_val"] == 42
        assert vertex["float_val"] == 3.14
        assert vertex["str_val"] == "hello"
        assert vertex["bool_val"] is True
        assert vertex["list_val"] == [1, 2, 3]
        assert vertex["none_val"] is None

    def test_vertex_empty_string_key(self) -> None:
        """Test vertex with empty string as key."""
        vertex = Vertex({"": "empty_key", "normal": "value"})

        assert vertex[""] == "empty_key"
        assert vertex["normal"] == "value"
        assert "" in vertex

    def test_vertex_hash_with_zero_value(self) -> None:
        """Test custom hash with zero value."""
        vertex = Vertex({"x": 10}, hash_value=0)

        assert hash(vertex) == 0
        assert vertex.to_dict()["_hash"] == 0
