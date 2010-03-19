from gsdll import CShadow, lgs
from core import Vertex, Edge

from ctypes import Structure, c_int, c_void_p, pointer, addressof, byref

class Vector(Structure):
    _fields_ = [("num_elements", c_int),
                ("num_alloc", c_int),
                ("expand_delta", c_int),
                ("elements", c_void_p)]
                
    def __new__(cls, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = lgs.vecNew( init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        
        # keep a reference to lgs in the instance so it doesn't get GCd prematurely
        self.lgs = lgs
        
        # addressof also tends to get GCd prematurely, so keep our own reference to our address
        self.address = addressof(self)
        
    def __del__(self):
        self.lgs.vecDestroy( self.address )
        
    def expand(self, amount):
        self.lgs.vecExpand( self.address, amount )
        
    def add(self, element):
        self.lgs.vecAdd( self.address, element )
        
    def get(self, index):
        return self.lgs.vecGet( self.address, index )

    
    
    
    