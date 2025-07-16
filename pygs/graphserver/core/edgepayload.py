from _ctypes import Py_DECREF, Py_INCREF
from ctypes import c_int, c_long, py_object, pythonapi

from ..gsdll import CShadow, cproperty, instantiate, lgs
from .walkable import Walkable


class EdgePayload(CShadow, Walkable):
    _registry = {}

    def __init__(self):
        if self.__class__ == EdgePayload:
            raise "EdgePayload is an abstract type."

    def destroy(self):
        self.check_destroyed()

        self._cdel(self.soul)
        self.soul = None

    def __str__(self):
        return self.to_xml()

    def to_xml(self):
        self.check_destroyed()
        return "<abstractedgepayload type='%s'/>" % self.type

    type = cproperty(lgs.epGetType, c_int)
    external_id = cproperty(lgs.epGetExternalId, c_long, setter=lgs.epSetExternalId)

    @classmethod
    def register_subclass(cls, type_id, subclass):
        """Register a subclass with its type ID."""
        cls._registry[type_id] = subclass

    @classmethod
    def from_pointer(cls, ptr):
        """Overrides the default behavior to return the appropriate subtype."""
        if ptr is None:
            return None

        type_id = lgs.epGetType(ptr)
        payloadtype = cls._registry.get(type_id)

        if payloadtype is None:
            raise ValueError(f"Unknown EdgePayload type: {type_id}")

        # Import here to avoid circular imports
        from .genericpypayload import GenericPyPayload

        if payloadtype is GenericPyPayload:
            p = lgs.cpSoul(ptr)
            # this is required to prevent garbage collection of the object
            Py_INCREF(p)
            return p
        ret = instantiate(payloadtype)
        ret.soul = ptr
        return ret


EdgePayload._cget_type = lgs.epGetType
EdgePayload._cwalk = lgs.epWalk
EdgePayload._cwalk_back = lgs.epWalkBack
