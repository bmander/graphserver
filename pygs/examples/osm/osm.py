from xml.dom.minidom import parseString
import copy
from pyproj import Proj, transform

class Node:
    def __init__(self, data):
        self.id  = int( data.attributes['id'].nodeValue )
        self.lat = float( data.attributes['lat'].nodeValue )
        self.lon = float( data.attributes['lon'].nodeValue )
        
        self.tags = {}
        for tag in data.getElementsByTagName("tag"):
            k = tag.attributes['k'].nodeValue
            v = tag.attributes['v'].nodeValue
            self.tags[k] = v
            
    def __repr__(self):
        return "<Node lon=%f lat=%f>"%(self.lon, self.lat)

def dist(x1,y1,x2,y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5
    
utmzone10 = Proj(init='epsg:26910')

class Way:
    def __init__(self, data, osm):
        self.osm = osm
        self.id = data.attributes['id'].nodeValue
        
        self.nodes = []
        for nd in data.getElementsByTagName("nd"):
            self.nodes.append( int( nd.attributes['ref'].nodeValue ) )
            
        self.tags = {}
        for tag in data.getElementsByTagName("tag"):
            k = tag.attributes['k'].nodeValue
            v = tag.attributes['v'].nodeValue
            self.tags[k] = v
    
    def split(self, dividers):
        # slice the node-array using this nifty recursive function
        def slice_array(ar, dividers):
            for i in range(1,len(ar)-1):
                if dividers[ar[i]]>1:
                    #print "slice at %s"%ar[i]
                    left = ar[:i+1]
                    right = ar[i:]
                    
                    rightsliced = slice_array(right, dividers)
                    
                    return [left]+rightsliced
            return [ar]
            
        slices = slice_array(self.nodes, dividers)
        
        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nodes = slice
            ret.append( littleway )
            i += 1
            
        return ret
        
    def get_projected_points(self ):
        ret = []
        for nodeid in self.nodes:
            node = self.osm.nodes[ nodeid ]
            ret.append( utmzone10(node.lon,node.lat) )
            
        return ret
    
    @property
    def length(self):
        ret = 0
        
        for i in range(len(self.nodes)-1):
            thisnode = self.osm.nodes[ self.nodes[i] ]
            nextnode = self.osm.nodes[ self.nodes[i+1] ]
            
            fromx, fromy = utmzone10(thisnode.lon,thisnode.lat)
            tox, toy = utmzone10(nextnode.lon,nextnode.lat)
            
            ret += dist(fromx,fromy,tox,toy)
        
        return ret
        
    @property
    def fromv(self):
        return self.nodes[0]
        
    @property
    def tov(self):
        return self.nodes[-1]

class OSM:
    def __init__(self, data):
        self.nodes = {}
        self.ways = {}
        
        dom = parseString( data )
        
        for node in dom.getElementsByTagName("node"):
            self.nodes[ int( node.attributes['id'].nodeValue ) ] = Node(node)
            
        for way in dom.getElementsByTagName("way"):
            self.ways[ way.attributes['id'].nodeValue ] = Way(way, self)
            
        del( dom )
            
        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        for way in self.ways.values():
            for node in way.nodes:
                node_histogram[node] += 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways
