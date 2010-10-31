import xml.sax
import copy
from math import *
from graphserver.vincenty import vincenty

INFINITY = float('inf')

def download_osm(left,bottom,right,top):
    """ Return a filehandle to the downloaded data."""
    from urllib.request import urlopen
    fp = urlopen( "http://api.openstreetmap.org/api/0.5/map?bbox=%f,%f,%f,%f"%(left,bottom,right,top) )
    return fp

def dist(x1,y1,x2,y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5

def dist_haversine(x0,y0,x1,y1):
    # Use spherical geometry to calculate the surface distance, in meters
    # between two geodesic points. Uses Haversine formula:
    # http://en.wikipedia.org/wiki/Haversine_formula
    radius = 6371000 # Earth mean radius in m
    lon0 = x0 * PI / 180 #rad
    lat0 = y0 * PI / 180 #rad
    lon1 = x1 * PI / 180 #rad
    lat1 = y1 * PI / 180 #rad
    dLat = (lat1 - lat0) #rad
    dLon = (lon1 - lon0) #rad
    a = sin(dLat/2) * sin(dLat/2) + cos(lat0) * cos(lat1) * sin(dLon/2) * sin(dLon/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return radius * c

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}

    def __repr__(self):
        return "<Node id='%s' (%s, %s) n_tags=%d>"%(self.id, self.lon, self.lat, len(self.tags))
        
class Way:
    def __init__(self, id, osm, tolerant=False):
        self.osm = osm
        self.id = id
        self.nd_ids = []
        self.tags = {}
        self.tolerant = tolerant #skip over dangling nd references
    
    @property
    def nds(self):
        for nd_id in self.nd_ids:
            try:
                yield self.osm.nodes[nd_id]
            except KeyError:
                if self.tolerant:
                    pass
                else:
                    raise KeyError( "Way references undefined node '%s'"%nd_id )
    @property
    def geom(self):
        return [(nd.lon, nd.lat) for nd in self.nds]
            
    @property
    def bbox(self):
        l = INFINITY
        b = INFINITY
        r = -INFINITY
        t = -INFINITY
        for x,y in self.geom:
            l = min(l,x)
            r = max(r,x)
            b = min(b,y)
            t = max(t,y)
        return (l,b,r,t)
    
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

        slices = slice_array(self.nd_ids, dividers)

        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nd_ids = slice
            ret.append( littleway )
            i += 1

        return ret

    def get_projected_points(self, reprojection_func=lambda x,y:(x,y)):
        """nodedir is a dictionary of nodeid->node objects. If reprojection_func is None, returns unprojected points"""
        ret = []

        for nodeid in self.nd_ids:
            node = self.osm.nodes[ nodeid ]
            ret.append( reprojection_func(node.lon,node.lat) )

        return ret

    def to_canonical(self, srid, reprojection_func=None):
        """Returns canonical string for this geometry"""

        return "SRID=%d;LINESTRING(%s)"%(srid, ",".join( ["%f %f"%(x,y) for x,y in self.get_projected_points()] ) )


    def length(self):
        """nodedir is a dictionary of nodeid->node objects"""
        ret = 0

        for i in range(len(self.nd_ids)-1):
            thisnode = self.osm.nodes[ self.nd_ids[i] ]
            nextnode = self.osm.nodes[ self.nd_ids[i+1] ]

            ret += vincenty(thisnode.lat, thisnode.lon, nextnode.lat, nextnode.lon)

        return ret

    def length_haversine(self):
        ret = 0

        for i in range(len(self.nds)-1):
            thisnode = self.osm.nodes[ self.nds[i] ]
            nextnode = self.osm.nodes[ self.nds[i+1] ]
            ret += dist(thisnode.lon,thisnode.lat,nextnode.lon,nextnode.lat)

        return ret

    @property
    def fromv(self):
        return self.nd_ids[0]

    @property
    def tov(self):
        return self.nd_ids[-1]
        
    def __repr__(self):
        return "<Way id='%s' n_nds=%d n_tags=%d>"%(self.id, len(self.nd_ids), len(self.tags))

class OSM:

    def __init__(self, filename_or_stream, tolerant=False):
        """ File can be either a filename or stream/file object."""
        nodes = {}
        ways = {}

        superself = self

        class OSMHandler(xml.sax.ContentHandler):
            @classmethod
            def setDocumentLocator(self,loc):
                pass

            @classmethod
            def startDocument(self):
                pass

            @classmethod
            def endDocument(self):
                pass

            @classmethod
            def startElement(self, name, attrs):
                if name=='node':
                    self.currElem = Node(attrs['id'], float(attrs['lon']), float(attrs['lat']))
                elif name=='way':
                    self.currElem = Way(attrs['id'], superself, tolerant)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nd_ids.append( attrs['ref'] )

            @classmethod
            def endElement(self,name):
                if name=='node':
                    nodes[self.currElem.id] = self.currElem
                elif name=='way':
                    ways[self.currElem.id] = self.currElem

            @classmethod
            def characters(self, chars):
                pass

        xml.sax.parse(filename_or_stream, OSMHandler)

        self.nodes = nodes
        self.ways = ways

        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        
        todel = []
        for way in self.ways.values():
            if len(way.nd_ids) < 2:       #if a way has only one node, delete it out of the osm collection
                todel.append( way.id )
        #have to do it in two passes, or else you change the size of dict during iteration
        for way_id in todel:
            del self.ways[way_id]

        for way in self.ways.values():
            for node in way.nd_ids:
                try:
                    node_histogram[node] += 1
                except KeyError:
                    node_histogram[node] = 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.items():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways

    @property
    def connecting_nodes(self):
        """List of nodes that are the endpoint of one or more ways"""

        ret = {}
        for way in self.ways.values():
            ret[way.fromv] = self.nodes[way.fromv]
            ret[way.tov] = self.nodes[way.tov]

        return ret.values()

    @classmethod
    def download_from_bbox(cls, left, bottom, right, top ):
        """ Retrieve remote OSM data."""
        fp = download_osm(left, bottom, right, top)
        osm = cls(fp)
        fp.close()
        return osm

    def find_nearest_node(self, lng, lat):
        """ Brute force effort to find the nearest start or end node based on lat/lng distances."""
        best = self.nodes[self.ways[self.ways.keys()[0]].nd_ids[0]]
        bdist = dist(best.lon, best.lat, lng, lat)
        for id, way in self.ways.iteritems():
            for i in (0,-1):
                nd = self.nodes[way.nd_ids[i]]
                d = dist(lng, lat, nd.lon, nd.lat)
                if d < bdist:
                    bdist = d
                    best = nd
        return best
    
    @property
    def bbox(self):
        l = INFINITY
        b = INFINITY
        r = -INFINITY
        t = -INFINITY
        
        for way in self.ways.values():
            ll, bb, rr, tt = way.bbox
            l = min(l,ll)
            b = min(b,bb)
            r = max(r,rr)
            t = max(t,tt)
            
        return (l,b,r,t)
        
