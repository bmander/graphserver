
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE
from ctypes import string_at, byref, c_int, c_long, c_size_t, c_char_p, c_double, c_void_p
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

def cleanup():
    #lgeos.finishGEOS()
    pass

atexit.register(cleanup)

#lgeos.initGEOS(notice_h, error_h)

def pycapi(func, rettype, cargs=None):
    func.restype = rettype
    if cargs:
        func.argtypes = cargs
        

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
pycapi(lgs.vGetOutgoingEdgeList, c_void_p, [c_void_p])
pycapi(lgs.vGetIncomingEdgeList, c_void_p, [c_void_p])

