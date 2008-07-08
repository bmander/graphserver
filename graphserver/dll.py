
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p, py_object
from ctypes import Structure, pointer, cast, POINTER, addressof

from ctypes.util import find_library
import os
import sys

# Try the major versioned name first, falling back on the unversioned name.
if 'GRAPHS_CORE_SO' in os.environ:
    so_loc = os.environ['GRAPHS_CORE_SO']
else:
    import settings
    so_loc = settings.GRAPHS_CORE_SO
    
lgs = PyDLL( so_loc )

free = CDLL('libc.so.6').free

import copy
def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = copy._EmptyClass()
    ret.__class__ = cls
    return ret

def cleanup():
    #lgeos.finishGEOS()
    pass

atexit.register(cleanup)

#lgeos.initGEOS(notice_h, error_h)

class CShadow():
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(cls)
        ret.soul = ptr
        return ret

def pycapi(func, rettype, cargs=None):
    func.restype = rettype
    if cargs:
        func.argtypes = cargs

def cproperty(cfunc, restype, ptrclass=None, setter=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    
    cfunc.restype = restype
    cfunc.argtypes = [c_void_p]
    if ptrclass:
        def prop(self):
            ret = cfunc( c_void_p( self.soul ) )
            return ptrclass.from_pointer(ret)
    else:
        def prop(self):
            return  cfunc( c_void_p( self.soul ) )
    if not setter:
        return property(prop)
    
    setter.restype.argtypes = [c_void_p, restype]
    if ptrclass:        
        def set(self, arg):
            if arg:
                setter(self.soul, arg.soul)
            else:
                setter(self.soul, None)
    else:
        def set(self, arg):
            setter(self.soul, arg)
    
    return property(prop, set)

def ccast(func, cls):
    """Wraps a function to casts the result of a function (assumed c_void_p)
       into an object using the class's from_pointer method."""
    func.restype = c_void_p
    def _cast(self, *args):
        return cls.from_pointer(func(*args))
    return _cast
        

# GRAPH API        
pycapi(lgs.gNew, c_void_p)
pycapi(lgs.gDestroy, c_void_p, [c_void_p,c_int,c_int])
pycapi(lgs.gAddVertex, c_void_p, [c_void_p, c_char_p])
pycapi(lgs.gGetVertex, c_void_p, [c_void_p, c_char_p])
pycapi(lgs.gAddEdge, c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p])
pycapi(lgs.gVertices, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.gShortestPathTree,c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p])
pycapi(lgs.gShortestPathTreeRetro,c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p])

# CALENDAR API 
pycapi(lgs.calNew, c_void_p, [c_long, c_long, c_int, c_void_p, c_int])
pycapi(lgs.calAppendDay, c_void_p, [c_void_p, c_long, c_long, c_int, c_void_p, c_int])
pycapi(lgs.calRewind, c_void_p, [c_void_p])
pycapi(lgs.calFastForward, c_void_p, [c_void_p])
pycapi(lgs.calDayOfOrAfter, c_void_p, [c_void_p, c_long])
pycapi(lgs.calDayOfOrBefore, c_void_p, [c_void_p, c_long])

# STATE API
pycapi(lgs.stateNew, c_void_p, [c_long])
pycapi(lgs.stateDup, c_void_p)

#VERTEX API
pycapi(lgs.vNew, c_void_p, [c_char_p])
pycapi(lgs.vDestroy, c_void_p, [c_void_p,c_int,c_int])
pycapi(lgs.vDegreeIn, c_int, [c_void_p])
pycapi(lgs.vDegreeOut, c_int, [c_void_p])
pycapi(lgs.vGetOutgoingEdgeList, c_void_p, [c_void_p])
pycapi(lgs.vGetIncomingEdgeList, c_void_p, [c_void_p])

#EDGE API
pycapi(lgs.eNew, c_void_p, [c_void_p, c_void_p, c_void_p])
pycapi(lgs.eGetFrom, c_void_p, [c_void_p])
pycapi(lgs.eGetTo, c_void_p, [c_void_p])
pycapi(lgs.eGetPayload, c_void_p, [c_void_p])
pycapi(lgs.eWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.eWalkBack, c_void_p, [c_void_p, c_void_p])

#EDGEPAYLOAD API
pycapi(lgs.epGetType, c_int, [c_void_p])
pycapi(lgs.epWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.epWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.epCollapse, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.epCollapseBack, c_void_p, [c_void_p, c_void_p])

#LINKNODE API
pycapi(lgs.linkNew, c_void_p)
pycapi(lgs.linkWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.linkWalkBack, c_void_p, [c_void_p, c_void_p])

#STREET API
pycapi(lgs.streetNew, c_void_p, [c_char_p, c_double])
pycapi(lgs.streetWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.streetWalkBack, c_void_p, [c_void_p, c_void_p])

#TRIPHOPSCHEDULE API
pycapi(lgs.thsNew, c_void_p) # args are dynamic, and not specified
pycapi(lgs.thsGetHop, c_void_p, [c_void_p, c_int])
pycapi(lgs.thsWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.thsWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.thsCollapse, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.thsCollapseBack, c_void_p, [c_void_p, c_void_p])

#TRIPHOP API
pycapi(lgs.triphopWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.triphopWalkBack, c_void_p, [c_void_p, c_void_p])

#CUSTOM TYPE API
class PayloadMethodTypes:
    destroy = CFUNCTYPE(c_void_p, c_void_p)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p)
    collapse = CFUNCTYPE(c_void_p, py_object, c_void_p)
    collapse_back = CFUNCTYPE(c_void_p, py_object, c_void_p)
    
pycapi(lgs.cpSoul, py_object, [c_void_p])
lgs.defineCustomPayloadType.restype = c_void_p
"""
pycapi(lgs.defineCustomPayloadType, 
       c_void_p, [PayloadMethodTypes.destroy, 
                  PayloadMethodTypes.walk,
                  PayloadMethodTypes.walk_back,
                  PayloadMethodTypes.collapse,
                  PayloadMethodTypes.collapse_back])
"""