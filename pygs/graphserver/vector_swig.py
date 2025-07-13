"""
SWIG-based Vector wrapper that provides the same interface as the ctypes version.
This is a drop-in replacement for the ctypes Vector implementation.
"""

import sys
import os

# Try to import SWIG module - fall back to core build
try:
    core_dir = os.path.join(os.path.dirname(__file__), '../../core')
    if core_dir not in sys.path:
        sys.path.insert(0, core_dir)
    import vector_swig as _swig_vector
except ImportError as e:
    raise ImportError(f"Could not import SWIG vector module: {e}")


class Vector:
    """SWIG-based Vector wrapper that mimics the ctypes interface."""
    
    def __init__(self, init_size=50, expand_delta=50):
        # Use the raw SWIG functions instead of the wrapped methods
        self._vector_ptr = _swig_vector.vecNew(init_size, expand_delta)
        self._init_size = init_size
        self._expand_delta = expand_delta
    
    @property
    def num_elements(self):
        # Access the struct members directly would be ideal, but we need
        # to create a temporary Vector object to access them
        temp_vector = _swig_vector.Vector.__new__(_swig_vector.Vector)
        temp_vector.this = self._vector_ptr
        return temp_vector.num_elements
    
    @property 
    def num_alloc(self):
        temp_vector = _swig_vector.Vector.__new__(_swig_vector.Vector)
        temp_vector.this = self._vector_ptr  
        return temp_vector.num_alloc
    
    @property
    def expand_delta(self):
        temp_vector = _swig_vector.Vector.__new__(_swig_vector.Vector)
        temp_vector.this = self._vector_ptr
        return temp_vector.expand_delta
    
    def expand(self, amount):
        _swig_vector.vecExpand(self._vector_ptr, amount)
    
    def add(self, element):
        # Convert Python integers to void pointer
        if isinstance(element, int):
            # Convert integer to void pointer value - this is what ctypes does
            _swig_vector.vecAdd(self._vector_ptr, element)
        else:
            try:
                element = int(element)
                _swig_vector.vecAdd(self._vector_ptr, element)
            except (ValueError, TypeError):
                raise TypeError(f"Cannot add element of type {type(element)} to Vector")
    
    def get(self, index):
        # Get the value and convert back to integer
        result = _swig_vector.vecGet(self._vector_ptr, index)
        # The C function returns NULL (which becomes 0) for out of bounds
        # We need to distinguish between a stored 0 and an out-of-bounds access
        # Check if the index is valid first
        if index < 0 or index >= self.num_elements:
            return None
        return result if result is not None else 0
        
    def __repr__(self):
        return f"<Vector SWIG shadow of {hex(self._vector_ptr)} ({self.num_elements}/{self.num_alloc})>"
    
    def __del__(self):
        # Clean up the C memory when the Python object is destroyed
        if hasattr(self, '_vector_ptr') and self._vector_ptr:
            _swig_vector.vecDestroy(self._vector_ptr)