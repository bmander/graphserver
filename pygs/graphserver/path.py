from gsdll import CShadow, lgs
from core import Vertex, Edge

class Path(CShadow):
    def __init__(self, origin):
        self.soul = lgs.pathNew( origin.soul )

    def destroy(self):
        lgs.pathDestroy( self.soul )

    def getSize(self):
        return lgs.pathGetSize( self.soul )
        
    def addSegment( self, vertex, edge ):
        lgs.pathAddSegment( self.soul, vertex.soul, edge.soul )
        
    def getVertex( self, i ):
        vertex_soul = lgs.pathGetVertex( self.soul, i )
        
        if vertex_soul==0:
            raise IndexError("%d is out of bounds"%i)
        
        return Vertex.from_pointer( vertex_soul )
        
    def getEdge( self, i ):
        edge_soul = lgs.pathGetEdge( self.soul, i )
        
        if edge_soul == 0:
            raise IndexError("%d is out of bounds"%i)
            
        return Edge.from_pointer( edge_soul )
