from .edgepayload import EdgePayload
from ..gsdll import c_void_p, cproperty, lgs, PayloadMethodTypes
from ctypes import py_object
from .util import failsafe
from .state import State
from .walkoptions import WalkOptions


class GenericPyPayload(EdgePayload):
    """This class is the base type for custom payloads created in Python.
    Subclasses can override the *_impl methods, which will be invoked through
    C callbacks."""

    def __init__(self):
        """Children MUST call this method to properly
        register themselves in C world."""
        self.soul = self._cnew(py_object(self), self._cmethods)
        self.name = self.__class__.__name__
        # required to keep this object around in the C world
        Py_INCREF(self)

    def to_xml(self):
        return "<pypayload type='%s' class='%s'/>" % (
            self.type,
            self.__class__.__name__,
        )

    """ These methods are the public interface, BUT should not be overridden by subclasses 
        - subclasses should override the *_impl methods instead."""

    @failsafe(1)
    def walk(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_impl(s, walkoptions)

    @failsafe(1)
    def walk_back(self, state, walkoptions):
        s = state.clone()
        s.prev_edge_name = self.name
        return self.walk_back_impl(s, walkoptions)

    """ These methods should be overridden by subclasses as deemed fit. """

    def walk_impl(self, state, walkoptions):
        return state

    def walk_back_impl(self, state, walkoptions):
        return state

    """ These methods provide the interface from the C world to py method implementation. """

    def _cwalk(self, stateptr, walkoptionsptr):
        return self.walk(
            State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)
        ).soul

    def _cwalk_back(self, stateptr, walkoptionsptr):
        return self.walk_back(
            State.from_pointer(stateptr), WalkOptions.from_pointer(walkoptionsptr)
        ).soul

    def _cfree(self):
        # print("Freeing %s..." % self)
        # After this is freed in the C world, this can be freed
        Py_DECREF(self)
        self.soul = None

    _cmethodptrs = [
        PayloadMethodTypes.destroy(_cfree),
        PayloadMethodTypes.walk(_cwalk),
        PayloadMethodTypes.walk_back(_cwalk_back),
    ]

    _cmethods = lgs.defineCustomPayloadType(*_cmethodptrs)


GenericPyPayload._cnew = lgs.cpNew
GenericPyPayload._cdel = lgs.cpDestroy

EdgePayload.register_subclass(4, GenericPyPayload)
