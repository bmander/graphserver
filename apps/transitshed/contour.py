from quikgrid import SurfaceGrid
import numpy

INFINITY = float('inf')

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i],ary[i+1])

class Times:
    def __init__(self, filename):
        self.times = set()
        
        fp = open( filename )
        for line in fp.readlines():
            x,y,z = tuple([float(x) for x in line.split(",")])
            self.times.add( (x,y,z) )
    
    @property
    def bounds(self):
        l = INFINITY
        b = INFINITY
        r = -INFINITY
        t = -INFINITY
        
        for x,y,z in self.times:
            l = min(l,x)
            b = min(b,y)
            r = max(r,x)
            t = max(t,y)
            
        return (l,b,r,t)

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

def travel_time_contour(points, cutoff=30*60, fudge=1.1, margin=2, closure_tolerance=0.05, cellsize=0.005):
    l, b, r, t = bounds(points)
    xspan = r-l
    yspan = t-b
    
    sg = SurfaceGrid( int(xspan/cellsize)+margin*2, int(yspan/cellsize)+margin*2, (l-cellsize*margin,b-cellsize*margin), (r+cellsize*margin,t+cellsize*margin) )
    sg.expand( points )
    
    mat = sg.to_matrix()
    for i, row in enumerate(mat):
        for j, (x,y,z) in enumerate(row): # x, y, height
            if z > cutoff or numpy.isnan(z):
                sg.setZ(i,j,cutoff*fudge)
    
    return sg.contour( cutoff, closure_tolerance=0.05 )

if __name__=='__main__':
    points = Times("portland.times").times
    
    l, b, r, t = bounds(points)
    
    ttc = travel_time_contour( points )
    
    from renderer.processing import MapRenderer
    mr = MapRenderer("./renderer/application.linux/renderer")
    mr.start(l, b, r, t, 1000)
    mr.smooth()
    mr.background( 255, 255, 255 )
    
    for c in ttc:
        coords = list(c)
        for (x1,y1), (x2,y2) in cons(coords):
            mr.line(x1,y1,x2,y2)
    
    
    mr.saveLocal( "contour.png" )
    mr.stop()