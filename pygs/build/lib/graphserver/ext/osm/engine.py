import sys
sys.path.append('../../..')
from graphserver.engine import Engine
from graph import OSMGraph
import re
_rc = re.compile


class OSMEngine(Engine):
    """ Provides additional methods for inspecting an OSMGraph. """
    def _nodes(self, w):
        osm = self.graph.osm
        ret = ["<?xml version='1.0'?><way>"]
        for way in osm.ways.values():
            if way.tags.get('name',"") == w:
                for n in way.nds:
                    ret.append("<node>%s</node>" % n)
        ret.append("</way>")
        return "".join(ret)
    _nodes.path = _rc(r"/nodes")
    _nodes.args = ("w",)
    
    
    def _intersection(self, a, b):
        osm = self.graph.osm
        a = osm.ways[a]
        b = osm.ways[b]
        ret = ["<?xml version='1.0'?><intersections>"]
        for n in a.nds:
            if n in b.nds:
                ret.append("<node>%s</node>" % n)
        ret.append("</intersections>")
        return "".join(ret)
    _intersection.path = _rc(r"/intersection")
    _intersection.args = ("a", "b")
    
    def _ways(self):
        osm = self.graph.osm
        ret = ["<?xml version='1.0'?><ways>"]
        for wayid, way in osm.ways.iteritems():
            ret.append("<way id='%s' name='%s'/>" % (wayid, way.tags.get('name',"").replace("'","\'")))
        ret.append("</ways>")
        return "".join(ret)
    _ways.path = _rc(r"/ways")
    _ways.args = None
    

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