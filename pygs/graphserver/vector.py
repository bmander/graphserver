from ctypes import Structure, addressof, c_int, c_void_p
from typing import Any

from .gsdll import lgs


class Vector(Structure):
    _fields_ = [
        ("num_elements", c_int),
        ("num_alloc", c_int),
        ("expand_delta", c_int),
        ("elements", c_void_p),
    ]

    def __new__(cls, init_size: int = 50, expand_delta: int = 50) -> "Vector":
        # initiate the Path Struct with a C constructor
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        soul = lgs.vecNew(init_size, expand_delta)

        # wrap an instance of this class around that pointer
        return cls.from_address(soul)

    def __init__(self, init_size: int = 50, expand_delta: int = 50) -> None:
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing

        pass

    def expand(self, amount: int) -> None:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        lgs.vecExpand(addressof(self), amount)

    def add(self, element: Any) -> None:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        lgs.vecAdd(addressof(self), element)

    def get(self, index: int) -> Any:
        if lgs is None:
            raise RuntimeError("libgraphserver not loaded")
        return lgs.vecGet(addressof(self), index)

    def __repr__(self) -> str:
        return "<Vector shadow of %s (%d/%d)>" % (
            hex(addressof(self)),
            self.num_elements,
            self.num_alloc,
        )
