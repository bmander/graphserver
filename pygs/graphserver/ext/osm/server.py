import sys
sys.path.append('../../..')
from graphserver.engine import XMLGraphEngine
from graphserver.server import GSHTTPServer, PORT, GSHTTPRequestHandler
from graph import OSMGraph
import re
_rc = re.compile


class OSMRequestHandler(GSHTTPRequestHandler):
    """ Provides additional methods for inspecting an OSMGraph. """
    def _nodes(self, w):
        osm = self.server.gengine.graph.osm
        ret = ["<?xml version='1.0'?><way>"]
        for way in osm.ways.values():
            if way.tags.get('name',"") == w:
                for n in way.nds:
                    ret.append("<node>%s</node>" % n)
        ret.append("</way>")
        return "".join(ret)
    
    
    def _intersection(self, a, b):
        osm = self.server.gengine.graph.osm
        a = osm.ways[a]
        b = osm.ways[b]
        ret = ["<?xml version='1.0'?><intersections>"]
        for n in a.nds:
            if n in b.nds:
                ret.append("<node>%s</node>" % n)
        ret.append("</intersections>")
        return "".join(ret)
    
    def _ways(self):
        osm = self.server.gengine.graph.osm
        ret = ["<?xml version='1.0'?><ways>"]
        for wayid, way in osm.ways.iteritems():
            ret.append("<way id='%s' name='%s'/>" % (wayid, way.tags.get('name',"").replace("'","\'")))
        ret.append("</ways>")
        return "".join(ret)
    
    urlpatterns = ((_rc(r"/nodes"),_nodes, ("w")),
                   (_rc(r"/intersection"),_intersection, ("a", "b")),
                   (_rc(r"/ways"), _ways, None)) + GSHTTPRequestHandler.urlpatterns
    

if __name__ == '__main__':
    import sys
    from pyproj import Proj
    if len(sys.argv) != 3:
        print "Usage: python %s <osm_datafile> <projection>\n" % (sys.argv[0])
    file = sys.argv[1]
    proj = Proj(init=sys.argv[2])
    g = OSMGraph(file, proj)
    s = GSHTTPServer(g, ('', PORT), OSMRequestHandler)
    s.run()