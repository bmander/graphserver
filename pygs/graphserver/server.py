import BaseHTTPServer
from SimpleHTTPServer import *
try: 
    from graphserver.engine import XMLGraphEngine
    from graphserver.core import Graph
except ImportError:
    from engine import XMLGraphEngine
    from core import Graph

import re
import cgi
import traceback, sys 
from types import *

_rc = re.compile

PORT = 7947

class GSHTTPRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    server_version = "PyGraphServer/1.0"
            
    def do_GET(self):
        
        for ppath, pfunc, pargs in self.urlpatterns():
            if ppath.match(self.path):
                args = {}
                if pargs and self.path.find("?") != -1:
                    args = cgi.parse_qs(self.path[self.path.index("?")+1:])
                    for k in args.keys():
                        args[k] = args[k][0]
                try:
                    r = pfunc(self,**args)
 
                    self.send_response(200)
                    self.send_header('Content-type', 'text/xml')
                    self.end_headers()
                    self.wfile.write(r)
                except:
                    traceback.print_exc()
                    self.log_error("Exception handling '%s'", self.path)
                    self.send_error(500)
                return
        # no match:
        self.send_response(200)
        self.send_header('Content-type', 'text/xml')
        self.end_headers()
        self.wfile.write(self._usage())
        

    def _shortest_path(self, **kw):
        return self.server.gengine.shortest_path(kw['from'],kw['to'],
                                                 time=int(kw.get('time',0)))
    _shortest_path.path = _rc(r'/shortest_path')
    _shortest_path.args    = ('from','to','time')
                                                 
    def _shortest_path_retro(self, **kw):
        return self.server.gengine.shortest_path_retro(kw['from'],kw['to'],
                                                       time=int(kw.get('time',0)))
    _shortest_path_retro.path = _rc(r'/shortest_path_retro')
    _shortest_path_retro.args = ('from','to','time')

    def _all_vertex_labels(self,**kw):
        return self.server.gengine.all_vertex_labels(**kw)
    _all_vertex_labels.path = _rc(r'/vertices')
    _all_vertex_labels.args = None
        
    def _collapse_edges(self,**kw):
        return self.server.gengine.collapse_edges(**kw)
    _collapse_edges.path = _rc(r'/vertex/outgoing/collapsed')
    _collapse_edges.args = ('label', 'time')

    def _walk_edges(self,**kw):
        return self.server.gengine.walk_edges(**kw)
    _walk_edges.path = _rc(r'/vertex/walk')
    _walk_edges.args = ('label', 'time')
        
    def _walk_edges_retro(self,**kw):
        return self.server.gengine.walk_edges_retro(**kw)
    _walk_edges_retro.path = _rc(r'/vertex/walk_retro')
    _walk_edges_retro.args = ('label', 'time')

    def _outgoing_edges(self,**kw):
        return self.server.gengine.outgoing_edges(**kw)
    _outgoing_edges.path = _rc(r'/vertex/outgoing')
    _outgoing_edges.args = ('label',)
    
    def _usage(self):
        ret = ["<?xml version='1.0'?><api>"]
        for pat in self.urlpatterns():
            ret.append("<method><path>%s</path><parameters>" % pat[0].pattern)
            if pat[2]:
                for p in pat[2]:
                    ret.append("<param>%s</param>" %p)
            ret.append("</parameters></method>")
        ret.append("</api>")
        return "".join(ret)

    @classmethod
    def urlpatterns(cls):
        ret = []
        
        for name in dir(cls):
            attr = getattr(cls, name)
            if type(attr) == UnboundMethodType and hasattr(attr, 'path') and hasattr(attr,'args'):
                ret.append( (attr.path, attr, attr.args) )
                
        return ret


class GSHTTPServer(BaseHTTPServer.HTTPServer):
    def __init__(self, gengine, *args):
        self.gengine = gengine
        BaseHTTPServer.HTTPServer.__init__(self, *args)
        
    def run(self):
        try:
            print "starting graphserver"
            self.serve_forever()
        except KeyboardInterrupt:
            print "^C received, shutting down."
            self.socket.close()
        
    
def test():
    import os, sys
    sys.path.append(os.path.dirname(__file__) + "/examples/hello_world")
    sys.path.append("examples/hello_world")
    from hello_world import HelloWorldEngine
    eng = HelloWorldEngine()
    print "using port %s" % PORT    
    httpd = GSHTTPServer(eng, ('', PORT), GSHTTPRequestHandler)
    httpd.run()     

if __name__ == '__main__':
    test()
