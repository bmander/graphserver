
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_float, c_size_t, c_char_p, c_double, c_void_p, py_object, c_bool
from ctypes import Structure, pointer, cast, POINTER, addressof
from ctypes.util import find_library

import os
import sys

# The libgraphserver.so object:
lgs = None

# Try loading from the source tree. If that doesn't work, fall back to the installed location.
_dlldirs = [os.path.dirname(os.path.abspath(__file__)),
            os.path.dirname(os.path.abspath(__file__)) + '/../../core',
            '/usr/lib',
            '/usr/local/lib']

for _dlldir in _dlldirs:
    _dllpath = os.path.join(_dlldir, 'libgraphserver.so')
    if os.path.exists(_dllpath):
        print _dllpath
        lgs = PyDLL( _dllpath )
        break

if not lgs:
    raise ImportError("unable to find libgraphserver shared library in the usual locations: %s" % "\n".join(_dlldirs))

libc = cdll.LoadLibrary(find_library('c'))


class _EmptyClass(object):
    pass

def instantiate(cls):
    """instantiates a class without calling the constructor"""
    ret = _EmptyClass()
    ret.__class__ = cls
    return ret

def cleanup():
    """ Perform any necessary cleanup when the library is unloaded."""
    pass

atexit.register(cleanup)

class CShadow(object):
    """ Base class for all objects that shadow a C structure."""
    @classmethod
    def from_pointer(cls, ptr):
        if ptr is None:
            return None
        
        ret = instantiate(cls)
        ret.soul = ptr
        return ret
        
    def check_destroyed(self):
        if self.soul is None:
            raise Exception("You are trying to use an instance that has been destroyed")

def pycapi(func, rettype, cargs=None):
    """Convenience function for setting arguments and return types."""
    func.restype = rettype
    if cargs:
        func.argtypes = cargs


def caccessor(cfunc, restype, ptrclass=None):
    """Wraps a C data accessor in a python function.
       If a ptrclass is provided, the result will be converted to by the class' from_pointer method."""
    cfunc.restype = restype
    cfunc.argtypes = [c_void_p]
    if ptrclass:
        def prop(self):
            self.check_destroyed()
            ret = cfunc( c_void_p( self.soul ) )
            return ptrclass.from_pointer(ret)
    else:
        def prop(self):
            self.check_destroyed()
            return cfunc( c_void_p( self.soul ) )
    return prop

def cmutator(cfunc, argtype, ptrclass=None):
    """Wraps a C data mutator in a python function.  
       If a ptrclass is provided, the soul of the argument will be used."""
    cfunc.argtypes = [c_void_p, argtype]
    if ptrclass:
        def propset(self, arg):
            cfunc( self.soul, arg.soul )
    else:
        def propset(self, arg):
            cfunc( self.soul, arg )
    return propset

def cproperty(cfunc, restype, ptrclass=None, setter=None):
    """if restype is c_null_p, specify a class to convert the pointer into"""
    if not setter:
        return property(caccessor(cfunc, restype, ptrclass))
    return property(caccessor(cfunc, restype, ptrclass),
                    cmutator(setter, restype, ptrclass))

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
pycapi(lgs.gShortestPathTree,c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p, c_int, c_long])
pycapi(lgs.gShortestPathTreeRetro,c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p, c_int, c_long])
pycapi(lgs.gSize,c_void_p, [c_long])
pycapi(lgs.sptPathRetro,c_void_p, [c_void_p, c_char_p, c_void_p])
pycapi(lgs.gShortestPathTreeRetro,c_void_p, [c_void_p, c_char_p, c_char_p, c_void_p, c_int, c_long])
pycapi(lgs.gSetVertexEnabled,c_void_p, [c_void_p, c_char_p, c_bool])

# SERVICE PERIOD API 
pycapi(lgs.spNew, c_void_p, [c_long, c_long, c_int, c_void_p])
pycapi(lgs.spRewind, c_void_p, [c_void_p])
pycapi(lgs.spFastForward, c_void_p, [c_void_p])
pycapi(lgs.spDatumMidnight, c_long, [c_void_p, c_int])
pycapi(lgs.spNormalizeTime, c_long, [c_void_p, c_int, c_long])

# SERVICE CALENDAR API
pycapi(lgs.scNew, c_void_p, [])
pycapi(lgs.scPeriodOfOrAfter, c_void_p, [c_void_p, c_int])
pycapi(lgs.scPeriodOfOrBefore, c_void_p, [c_void_p, c_int])
pycapi(lgs.scAddPeriod, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.scGetServiceIdInt, c_int, [c_void_p, c_char_p])
pycapi(lgs.scGetServiceIdString, c_char_p, [c_void_p, c_int])

# TIMEZONE PERIOD API
pycapi(lgs.tzpNew, c_void_p, [c_long, c_long, c_int])
pycapi(lgs.tzpDestroy, None, [c_void_p])
pycapi(lgs.tzpUtcOffset, c_int, [c_void_p])
pycapi(lgs.tzpBeginTime, c_long, [c_void_p])
pycapi(lgs.tzpEndTime, c_long, [c_void_p])
pycapi(lgs.tzpNextPeriod, c_void_p, [c_void_p])

# TIMEZONE API
pycapi(lgs.tzNew, c_void_p, [])
pycapi(lgs.tzAddPeriod, c_void_p, [c_void_p])
pycapi(lgs.tzPeriodOf, c_void_p, [c_void_p, c_long])
pycapi(lgs.tzUtcOffset, c_int, [c_void_p, c_long])
pycapi(lgs.tzHead, c_void_p, [c_void_p])

# STATE API
pycapi(lgs.stateNew, c_void_p, [c_int, c_long])
pycapi(lgs.stateDup, c_void_p)
pycapi(lgs.stateDestroy, c_void_p)
pycapi(lgs.stateServicePeriod, c_void_p, [c_int])

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
pycapi(lgs.eWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.eWalkBack, c_void_p, [c_void_p, c_void_p, c_int])

#EDGEPAYLOAD API
pycapi(lgs.epGetType, c_int, [c_void_p])
pycapi(lgs.epWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.epWalkBack, c_void_p, [c_void_p, c_void_p, c_int])

#LINKNODE API
pycapi(lgs.linkNew, c_void_p)
pycapi(lgs.linkDestroy, c_void_p)
pycapi(lgs.linkWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.linkWalkBack, c_void_p, [c_void_p, c_void_p])

#STREET API
pycapi(lgs.streetNew, c_void_p, [c_char_p, c_double])
pycapi(lgs.streetNewElev, c_void_p, [c_char_p, c_double, c_float, c_float])
pycapi(lgs.streetDestroy, c_void_p)
pycapi(lgs.streetWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.streetWalkBack, c_void_p, [c_void_p, c_void_p])

#EGRESS API
pycapi(lgs.egressNew, c_void_p, [c_char_p, c_double])
pycapi(lgs.egressDestroy, c_void_p)
pycapi(lgs.egressWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.egressWalkBack, c_void_p, [c_void_p, c_void_p])

#HEADWAY API
pycapi(lgs.headwayWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.headwayWalkBack, c_void_p, [c_void_p, c_void_p, c_int])

#TRIPBOARD API
pycapi(lgs.tbNew, c_void_p, [c_int, c_void_p, c_void_p, c_int])
pycapi(lgs.tbWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.headwayWalk, c_void_p, [c_void_p, c_void_p, c_int])
pycapi(lgs.tbAddBoarding, c_void_p, [c_void_p, c_char_p, c_int])
pycapi(lgs.tbGetBoardingTripId, c_char_p, [c_void_p, c_int])
pycapi(lgs.tbGetBoardingDepart, c_int, [c_void_p, c_int])

#ALIGHT API
pycapi(lgs.alGetAlightingTripId, c_char_p, [c_void_p, c_int])
pycapi(lgs.alGetAlightingArrival, c_int, [c_void_p, c_int])

#ELAPSE TIME API
pycapi(lgs.elapseTimeNew, c_void_p, [c_long])
pycapi(lgs.elapseTimeDestroy, c_void_p)
pycapi(lgs.elapseTimeWalk, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.elapseTimeWalkBack, c_void_p, [c_void_p, c_void_p])
pycapi(lgs.elapseTimeGetSeconds, c_long, [c_void_p])

#CUSTOM TYPE API
class PayloadMethodTypes:
    """ Enumerates the ctypes of the function pointers."""
    destroy = CFUNCTYPE(c_void_p, py_object)
    walk = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    walk_back = CFUNCTYPE(c_void_p, py_object, c_void_p, c_void_p)
    
pycapi(lgs.cpSoul, py_object, [c_void_p])
# args are not specified to allow for None
lgs.defineCustomPayloadType.restype = c_void_p
