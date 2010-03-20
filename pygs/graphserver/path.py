from gsdll import CShadow, lgs
from core import Vertex, Edge
from vector import Vector

from ctypes import Structure, c_int, c_void_p, pointer, addressof, byref, POINTER

class Path(Structure):
    _fields_ = [("vertices", POINTER(Vector)),
                ("edges", POINTER(Vector))]
                
    def __new__(cls, origin, init_size=50, expand_delta=50):
        # initiate the Path Struct with a C constructor
        soul = lgs.pathNew( origin.soul, init_size, expand_delta )
        
        # wrap an instance of this class around that pointer
        return cls.from_address( soul )
        
    def __init__(self, origin, init_size=50, expand_delta=50):
        # this gets called with the same arguments as __new__ right after
        # __new__ is called, but we've already constructed the struct, so
        # do nothing
        pass
        
    def addSegment(self, vertex, edge):
        lgs.pathAddSegment( addressof(self), vertex.soul, edge.soul )
        
    def getVertex( self, i ):
        vertex_soul = lgs.pathGetVertex( addressof(self), i )
        
        if vertex_soul==0:
            raise IndexError("%d is out of bounds"%i)
        
        return Vertex.from_pointer( vertex_soul )
        
    def getEdge( self, i ):
        edge_soul = lgs.pathGetEdge( addressof(self), i )
        
        if edge_soul == 0:
            raise IndexError("%d is out of bounds"%i)
            
        return Edge.from_pointer( edge_soul )
        
    @property
    def num_elements(self):
        return self.edges.contents.num_elements
        
if __name__=='__main__':
    path = Path( Vertex("A") )
    print path.size
    
