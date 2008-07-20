import xml.sax
import copy
  
def download_osm(left,bottom,right,top):
    """ Return a filehandle to the downloaded data."""
    from urllib import urlopen
    fp = urlopen( "http://api.openstreetmap.org/api/0.5/map?bbox=%f,%f,%f,%f"%(left,bottom,right,top) )
    return fp
  
def dist(x1,y1,x2,y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}
        
class Way:
    def __init__(self, id, osm):
        self.osm = osm
        self.id = id
        self.nds = []
        self.tags = {}
        
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
            
        slices = slice_array(self.nds, dividers)
        
        # create a way object for each node-array slice
        ret = []
        i=0
        for slice in slices:
            littleway = copy.copy( self )
            littleway.id += "-%d"%i
            littleway.nds = slice
            ret.append( littleway )
            i += 1
            
        return ret
        
    def get_projected_points(self, reprojection_func=lambda x,y:(x,y)):
        """nodedir is a dictionary of nodeid->node objects. If reprojection_func is None, returns unprojected points"""
        ret = []
        
        for nodeid in self.nds:
            node = self.osm.nodes[ nodeid ]
            ret.append( reprojection_func(node.lon,node.lat) )
            
        return ret
        
    def to_canonical(self, srid, reprojection_func=None):
        """Returns canonical string for this geometry"""
        
        return "SRID=%d;LINESTRING(%s)"%(srid, ",".join( ["%f %f"%(x,y) for x,y in self.get_projected_points()] ) )
        
        
    def length(self, reprojection_func=lambda x,y:(x,y)):
        """nodedir is a dictionary of nodeid->node objects"""
        ret = 0
        
        for i in range(len(self.nds)-1):
            thisnode = self.osm.nodes[ self.nds[i] ]
            nextnode = self.osm.nodes[ self.nds[i+1] ]
            
            fromx, fromy = reprojection_func(thisnode.lon,thisnode.lat)
            tox, toy = reprojection_func(nextnode.lon,nextnode.lat)
            
            ret += dist(fromx,fromy,tox,toy)
        
        return ret
        
    @property
    def fromv(self):
        return self.nds[0]
        
    @property
    def tov(self):
        return self.nds[-1]

class OSM:
    
    def __init__(self, filename_or_stream):
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
                    self.currElem = Way(attrs['id'], superself)
                elif name=='tag':
                    self.currElem.tags[attrs['k']] = attrs['v']
                elif name=='nd':
                    self.currElem.nds.append( attrs['ref'] )
                
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
        for way in self.ways.values():
            if len(way.nds) < 2:       #if a way has only one node, delete it out of the osm collection
                del self.ways[way.id]
            else:
                for node in way.nds:
                    node_histogram[node] += 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways

    @classmethod
    def download_from_bbox(cls, left, bottom, right, top ):
        """ Retrieve remote OSM data."""
        fp = download_osm(left, bottom, right, top)
        osm = cls(fp)
        fp.close()
        return osm

    def nearest_node(self, lng, lat):
        """ Brute force effort to find the nearest start or end node."""
        best = self.nodes[0]
        bdist = dist(best.lng,best.lat,lng,lat)
        for n in self.nodes:
            tdist = dist(best.lng,best.lat,n.lng,n.lat)
            if tdist < bdist:
                best = n
        return best
