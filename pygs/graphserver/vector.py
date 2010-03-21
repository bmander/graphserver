from gsdll import CShadow, lgs

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
        
        pass
        
    def expand(self, amount):
        lgs.vecExpand( addressof(self), amount )
        
    def add(self, element):
        lgs.vecAdd( addressof(self), element )
        
    def get(self, index):
        return lgs.vecGet( addressof(self), index )
        
    def __repr__(self):
        return "<Vector shadow of %s (%d/%d)>"%(hex(addressof(self)),self.num_elements, self.num_alloc)

    
    
    
    