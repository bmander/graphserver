from servable import Servable
from graphserver.graphdb import GraphDatabase
import time
from graphserver import core
from graphserver.core import State, WalkOptions
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.ext.gtfs.gtfsdb import GTFSDatabase
from graphserver.util import TimeHelpers
from contour import travel_time_contour, travel_time_surface, points_to_surface_grid
try:
    import json
except ImportError:
    import simplejson as json
from rtree import Rtree
from glineenc import encode_pairs
from urllib import urlopen
import yaml

def cons(ary):
    for i in range(len(ary)-1):
        yield ary[i],ary[i+1]
        
def frange(low,high,step):
    curs = low
    while curs<=high:
        yield curs
        curs += step

class ContourServer(Servable):
    def __init__(self, settings_filename):
        settings = yaml.load( open( settings_filename ) )
        
        self.home_point = settings['center']
        
        # create cache of osm-node positions
        self.osmdb = OSMDB( settings['osmdb_filename'] )
        self.gtfsdb = GTFSDatabase( settings['gtfsdb_filename'] )
        self.port = settings['port']
        self.node_positions = {}
        self.index = Rtree()
        for node_id, tags, lat, lon in self.osmdb.nodes():
            self.node_positions[node_id] = (lon,lat)
            self.index.add( int(node_id), (lon,lat,lon,lat) )
        
        # incarnate graph from graphdb
        graphdb = GraphDatabase( settings['graphdb_filename'] )
        self.graph = graphdb.incarnate()
    
    def strgraph(self):
        return str(self.graph)
    
    def vertices(self):
        return "\n".join( [vv.label for vv in self.graph.vertices] )
    
    def _get_important_routes(self, spt):
        # set edge thicknesses
        t0 = time.time()
        print "setting thicknesses"
        spt.set_thicknesses( vertex_label )
        t1 = time.time()
        print "took %s"%(t1-t0)
        
        t0 = time.time()
        print "finding gateway boardings"
        # use thicknesses to determine important boardings
        origin = spt.get_vertex( vertex_label )
        sum_thickness = sum( [edge.thickness for edge in origin.outgoing] )
        
        important_boardings = sorted( filter(lambda x: x.payload.__class__==core.TripBoard and \
                                                        x.thickness/float(sum_thickness) > 0.01, spt.edges),
                                      key = lambda x:x.thickness )
                                               
        for edge in important_boardings:
            print "gateway to %f%% vertices"%(100*edge.thickness/float(sum_thickness))
            print "hop onto trip '%s' at stop '%s', time '%s'"%(edge.to_v.payload.trip_id, edge.from_v.label, edge.to_v.payload.time)
        print "took %ss"%(time.time()-t0)
    
    def _points(self, vertex_label, starttime, cutoff, speed):
        starttime = starttime or time.time()
        
        #=== find shortest path tree ===
        print "Finding shortest path tree"
        t0 = time.time()
        wo = WalkOptions()
        wo.walking_speed = speed
        spt = self.graph.shortest_path_tree( vertex_label, None, State(1,starttime), wo, maxtime=starttime+int(cutoff*1.25) )
        wo.destroy()
        t1 = time.time()
        print "took %s s"%(t1-t0)
        
        #=== cobble together ETA surface ===
        print "Creating ETA surface from OSM points..."
        points = []
        t0 = time.time()
        for vertex in spt.vertices:
            if "osm" in vertex.label:
                x, y = self.node_positions[vertex.label[3:]]
                points.append( (x, y, vertex.payload.time-starttime) )
        t1 = time.time()
        print "Took %s s"%(t1-t0)
        
        spt.destroy()
        
        return points
    
    def _contour(self, vertex_label, starttime, cutoff, step=None, speed=0.85):
        points = self._points( vertex_label, starttime, cutoff, speed )
        
        #=== create contour ===
        print "creating contour...",
        
        t0 = time.time()
        contours = travel_time_contour( points, cutoff=cutoff, cellsize=0.004, fudge=1.7, step=step )
        print "%s sec"%(time.time()-t0)
        
        print "done. here you go..."
        return contours
    
    def label_contour(self, vertex_label, starttime=None, cutoff=1800):
        starttime = starttime or time.time()
        
        return json.dumps( self._contour( vertex_label, starttime, cutoff ) )
    
    def contour(self, lat, lon, year, month, day, hour, minute, second, cutoff, step=60*15, encoded=False, speed=0.85):
        if step is not None and step < 600:
            raise Exception( "Step cannot be less than 600 seconds" )
        
        starttime = TimeHelpers.localtime_to_unix( year, month, day, hour, minute, second, "America/Los_Angeles" )
        
        #=== get osm vertex ==
        print( "getting nearest vertex" )
        
        #find osmid of origin intersection
        t0 = time.time()
        range = 0.001
        bbox = (lon-range, lat-range, lon+range, lat+range)
        candidates = self.index.intersection( bbox )
        vlabel, vlat, vlon, vdist = self.osmdb.nearest_of( lat, lon, candidates )
        t1 = time.time()
        print( "done, took %s seconds"%(t1-t0) )
        
        #vlabel, vlat, vlon, vdist = self.osmdb.nearest_node( lat, lon )
        
        if vlabel is None:
            return json.dumps( "NO NEARBY INTERSECTION" )
        
        print( "found - %s"%vlabel )
        
        contours = self._contour( "osm"+vlabel, starttime, cutoff, step, speed )
        
        if encoded:
            encoded_contours = []
            for contour in contours:
                encoded_contour = []
                for ring in contour:
                    encoded_contour.append( encode_pairs( [(lat,lon) for lon,lat in ring] ) )
                encoded_contours.append( encoded_contour )
                
            contours = encoded_contours
        
        return json.dumps( contours )

    def _surface(self, lat, lon, year, month, day, hour, minute, second, cutoff, speed, cellsize=0.004):
        
        starttime = TimeHelpers.localtime_to_unix( year, month, day, hour, minute, second, "America/Los_Angeles" )
        
        #=== get osm vertex ==
        print( "getting nearest vertex" )
        
        #find osmid of origin intersection
        t0 = time.time()
        range = 0.001
        bbox = (lon-range, lat-range, lon+range, lat+range)
        candidates = self.index.intersection( bbox )
        vlabel, vlat, vlon, vdist = self.osmdb.nearest_of( lat, lon, candidates )
        t1 = time.time()
        print( "done, took %s seconds"%(t1-t0) )
        
        #vlabel, vlat, vlon, vdist = self.osmdb.nearest_node( lat, lon )
        
        if vlabel is None:
            return json.dumps( "NO NEARBY INTERSECTION" )
        
        print( "found - %s"%vlabel )
        
        #=== get points which comprise ETA surface ===
        points = self._points( "osm"+vlabel, starttime, cutoff, speed )
        
        #=== create regular grid from ETA surface ===
        print "creating surface...",
        
        t0 = time.time()
        ret = points_to_surface_grid( points, cutoff=cutoff, fudge=1.1, margin=2, closure_tolerance=0.05, cellsize=cellsize )
        #ret = travel_time_surface( points, cutoff=cutoff, cellsize=0.004, fudge=1.7 )
        print "%s sec"%(time.time()-t0)
        print "done. here you go..."
        
        return ret

    def surface(self, lat, lon, year, month, day, hour, minute, second, cutoff, speed=0.85):
        return json.dumps( self._surface(lat,lon,year,month,day,hour,minute,second,cutoff,speed).to_matrix() )
        
    def transitability(self, lat, lon, year, month, day, hour, minute, second, cutoff, speed=0.85):
        grid = self._surface(lat,lon,year,month,day,hour,minute,second,cutoff,speed)
        
        if type(grid) == str:
            return None
        
        ret = 0
        for i in range(10):
            contourslice=sum( [len(filter(lambda x:x[2]<=(cutoff/10.0)*(i+1),col)) for col in grid] )
            print contourslice
            ret += contourslice
        
        return ret
            
    def transitability_surface(self, left, bottom, right, top, res, year, month, day, hour, minute, second, cutoff, speed=0.85):
        step = (right-left)/res
        
        return json.dumps([[(lon,lat,self.transitability(lat,lon,year,month,day,hour,minute,second,cutoff,speed)) for lat in frange(bottom,top,step)] for lon in frange(left,right,step)])
        
    def nodes(self):
        return "\n".join( ["%s-%s"%(k,v) for k,v in self.node_positions.items()] )
            
    def nearest_node(self, lat, lon):
        range = 0.005
        bbox = (lon-range, lat-range, lon+range, lat+range)
        print bbox
        print self.index.intersection( bbox )
        
        return json.dumps(self.osmdb.nearest_node( lat, lon ))
        
    def bounds(self):
        return json.dumps(self.osmdb.bounds())
    
    def run_test_server(self):
        Servable.run_test_server(self, self.port)

# part of the transitabilty heatmap experiment. rightfully I should stick this in its own app.
def print_transitability_surface(cserver):
    print "bounds are %s"%cserver.bounds()
    
    bottom,left=(47.66567637286265, -122.33173370361328)
    top,right=(47.687405831555616, -122.30289459228516)
    
    print cserver.transitability_surface(left,bottom,right,top, 30, 2009, 2, 18, 12, 0, 0, 45*60)

from PIL import Image, ImageDraw
def save_eta_surface(settings_filename, width, fname):
    cserver = ContourServer( settings_filename )
    
    lat, lon =(47.68671247798501, -122.32057571411133)
    
    sg = cserver._surface(lat,lon, 2009, 2, 18, 12, 0, 0, 120*60, 1.0, cellsize=0.001)
    
    grid = sg.to_matrix()
    left,bottom,t = grid[0][0]
    right,top,t = grid[-1][-1]
    
    cellsize = (right-left)/width

    igrid = [[sg.interpolate(x,y) for x in frange(left,right,cellsize)] for y in frange(bottom,top, cellsize)]
        
    #fp = open(fname, "w")
    #fp.write( "\n".join([",".join(map(str,row)) for row in igrid]) )
    #fp.close()
    
    height = len(igrid)
    width = len(igrid[0])
    
    mintime = min([min(line) for line in igrid])
    maxtime = max([max(line) for line in igrid])
    
    #red to yellow (255,0,0) to (255,255,0)
    rty = zip([255]*256, range(256),[0]*256)
    #yellow to green (255,255,0) to (0,255,0)
    ytg = zip(range(255,-1,-1), [255]*256, [0]*256)
    #green to cyan (0,255,0) to (0,255,255)
    gtc = zip([0]*256, [255]*256, range(256))
    #cyan to blue (0,255,255) to (0,0,255)
    ctb = zip([0]*256, range(255,-1,-1), [255]*256)
    #blue to violet (0,0,255) to (255,0,255)
    btv = zip(range(256), [0]*256, [255]*256)

    colors = rty+ytg+gtc+ctb+btv
    
    im = Image.new("RGB", (width,height))
    draw = ImageDraw.Draw(im)
    for y, line in enumerate(igrid):
        for x, cell in enumerate(line):
            color = colors[int(((cell-mintime)/(maxtime-mintime))*(len(colors)-1))]
            draw.point( (x,y), fill=color )
            #print x, y, int(((cell-mintime)/(maxtime-mintime))*255)
    del draw 
    # write to stdout
    im.save(fname, "PNG")


def eta_main(settings_filename):
    save_eta_surface( "seattle.yaml", 1000, "grid.png" )

def main(settings_filename=None):
    from sys import argv

    usage = "python sptserver.py settings_filename"
    
    if settings_filename is None:
        if len(argv) < 2:
            print usage
            quit()
        else:
            settings_filename = argv[1]
    
    cserver = ContourServer( settings_filename )
    
    cserver.run_test_server()

if __name__=='__main__':
    main()

    
