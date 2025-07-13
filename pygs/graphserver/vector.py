from ctypes import Structure, addressof, c_int, c_void_p

from .gsdll import lgs

# Try to import SWIG version, fall back to ctypes if not available
try:
    from .vector_swig import Vector as SwigVector
    SWIG_AVAILABLE = True
except ImportError:
    SWIG_AVAILABLE = False


class Vector(Structure):
    _fields_ = [
        ("num_elements", c_int),
        ("num_alloc", c_int),
        ("expand_delta", c_int),
        ("elements", c_void_p),
    ]

    def __new__(cls, init_size=50, expand_delta=50):
        if SWIG_AVAILABLE:
            # Use SWIG implementation internally but maintain ctypes interface
            instance = Structure.__new__(cls)
            instance._swig_vector = SwigVector(init_size, expand_delta)
            instance._use_swig = True
            # Initialize ctypes fields to sync with SWIG values
            instance.num_elements = instance._swig_vector.num_elements
            instance.num_alloc = instance._swig_vector.num_alloc
            instance.expand_delta = instance._swig_vector.expand_delta
            instance.elements = 0  # Placeholder
            return instance
        else:
            # Fall back to original ctypes implementation
            soul = lgs.vecNew(init_size, expand_delta)
            return cls.from_address(soul)

    def __init__(self, init_size=50, expand_delta=50):
        # Both cases handled in __new__
        pass
    
    def _sync_fields(self):
        """Sync ctypes fields with SWIG values"""
        if hasattr(self, '_use_swig'):
            self.num_elements = self._swig_vector.num_elements
            self.num_alloc = self._swig_vector.num_alloc
            self.expand_delta = self._swig_vector.expand_delta

    def expand(self, amount):
        if hasattr(self, '_use_swig'):
            self._swig_vector.expand(amount)
            self._sync_fields()
        else:
            lgs.vecExpand(addressof(self), amount)

    def add(self, element):
        if hasattr(self, '_use_swig'):
            self._swig_vector.add(element)
            self._sync_fields()
        else:
            lgs.vecAdd(addressof(self), element)

    def get(self, index):
        if hasattr(self, '_use_swig'):
            return self._swig_vector.get(index)
        else:
            return lgs.vecGet(addressof(self), index)

    def __repr__(self):
        if hasattr(self, '_use_swig'):
            return "<Vector hybrid SWIG shadow of %s (%d/%d)>" % (
                hex(id(self._swig_vector)),
                self.num_elements,
                self.num_alloc,
            )
        else:
            return "<Vector shadow of %s (%d/%d)>" % (
                hex(addressof(self)),
                self.num_elements,
                self.num_alloc,
            )
