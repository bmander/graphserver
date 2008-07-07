import xml.sax
import copy
from pyproj import Proj, transform

def dist(x1,y1,x2,y2):
    return ((x2-x1)**2+(y2-y1)**2)**0.5
    
utmzone10 = Proj(init='epsg:26910')

class Node:
    def __init__(self, id, lon, lat):
        self.id = id
        self.lon = lon
        self.lat = lat
        self.tags = {}
        
class Way:
    def __init__(self, id):
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
        
    def get_projected_points(self, nodedir):
        """nodedir is a dictionary of nodeid->node objects"""
        ret = []
        for nodeid in self.nds:
            node = nodedir[ nodeid ]
            ret.append( utmzone10(node.lon,node.lat) )
            
        return ret
        
    def length(self, nodedir):
        """nodedir is a dictionary of nodeid->node objects"""
        ret = 0
        
        for i in range(len(self.nds)-1):
            thisnode = nodedir[ self.nds[i] ]
            nextnode = nodedir[ self.nds[i+1] ]
            
            fromx, fromy = utmzone10(thisnode.lon,thisnode.lat)
            tox, toy = utmzone10(nextnode.lon,nextnode.lat)
            
            ret += dist(fromx,fromy,tox,toy)
        
        return ret
        
    @property
    def fromv(self):
        return self.nds[0]
        
    @property
    def tov(self):
        return self.nds[-1]

class OSM:
    def __init__(self, filename):
        nodes = {}
        ways = {}
        
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
                    self.currElem = Way(attrs['id'])
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

        xml.sax.parse(filename, OSMHandler)
        
        self.nodes = nodes
        self.ways = ways
            
        #count times each node is used
        node_histogram = dict.fromkeys( self.nodes.keys(), 0 )
        for way in self.ways.values():
            for node in way.nds:
                node_histogram[node] += 1
        
        #use that histogram to split all ways, replacing the member set of ways
        new_ways = {}
        for id, way in self.ways.iteritems():
            split_ways = way.split(node_histogram)
            for split_way in split_ways:
                new_ways[split_way.id] = split_way
        self.ways = new_ways
    
if __name__=='__main__':
    osm = OSM("map.osm")
    for way in osm.ways.values():
        way.length(osm.nodes)