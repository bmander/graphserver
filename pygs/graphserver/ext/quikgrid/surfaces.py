from quikgrid import SurfaceGrid
import numpy

        
class CostSurface(SurfaceGrid):
    def __init__(self, points, max_value, 
                 fudge=1.7, 
                 surface_margin=2, 
                 cellsize=0.004):

        l, b, r, t = bounds(points)
        xspan = r-l
        yspan = t-b
        
        super(CostSurface, self).__init__( int(xspan/cellsize)+surface_margin*2, int(yspan/cellsize)+surface_margin*2, 
                                           (l-cellsize*surface_margin,b-cellsize*surface_margin), (r+cellsize*surface_margin,t+cellsize*surface_margin) )
        self.expand( points )
        
        mat = self.to_matrix()
        for i, row in enumerate(mat):
            for j, (x,y,z) in enumerate(row): # x, y, height
                if numpy.isnan(z):
                    self.setZ(i,j,max_value*fudge)
                #if z > cutoff or numpy.isnan(z):
                #    sg.setZ(i,j,cutoff*fudge)
        
        
    def contours(self, cutoff, step=None, closure_tolerance=0.05):
        ret = []
        if step is not None:
            for i in range( step, cutoff, step ):
                ret.append( self.contour( i, closure_tolerance=closure_tolerance) )
                
        ret.append( self.contour( cutoff, closure_tolerance=closure_tolerance ) )
        return ret

class SPTTimeSurface(CostSurface):
    """Builds a cost surface from a SPT using the state's time value."""
    def __init__(self, spt, starttime, max_cutoff, node_location_lookup, **kwargs):
        #import pdb
        #pdb.set_trace()
        points = []
        for vertex in spt.vertices:
            x,y = node_location_lookup(vertex.label)
            if x != None:
                points.append( (x, y, vertex.payload.time-starttime) )
        print "Points:", len(points)
        super(SPTTimeSurface, self).__init__(points, max_cutoff, **kwargs)

class SPTWeightSurface(CostSurface):
    """Builds a cost surface from a SPT using the state's weight value."""
    def __init__(self, spt, node_location_lookup, **kwargs):
        points = []
        max_weight = -INFINITY
        for vertex in spt.vertices:
            x,y = node_location_lookup(vertex)
            if x != None:
                w = vertex.payload.weight
                max_weight = max(w, max_weight)
                points.append( (x, y, vertex.payload.weight) )
        
        super(SPTWeightSurface, self).__init__(points, max_weight, **kwargs)


INFINITY = float('inf')

def bounds(points):
    l = INFINITY
    b = INFINITY
    r = -INFINITY
    t = -INFINITY
    
    for x,y,z in points:
        l = min(l,x)
        b = min(b,y)
        r = max(r,x)
        t = max(t,y)
        
    return (l,b,r,t)