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
                    fargs = [args.get(parg) for parg in pargs]
                    r = pfunc(self.server.gengine,*fargs)
 
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
    
    def _usage(self):
        ret = ["<?xml version='1.0'?><api>"]
        for ppath, pfunc, pargs in self.urlpatterns():
            ret.append("<method><path>%s</path><parameters>" % ppath.pattern)
            if pargs:
                for p in pargs:
                    ret.append("<param>%s</param>" %p)
            ret.append("</parameters></method>")
        ret.append("</api>")
        return "".join(ret)

    def urlpatterns(self):
        cls = self.server.gengine.__class__
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
