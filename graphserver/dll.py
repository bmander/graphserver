
import atexit
from ctypes import cdll, CDLL, pydll, PyDLL, CFUNCTYPE, c_char_p
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
