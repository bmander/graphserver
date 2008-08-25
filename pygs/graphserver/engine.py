try:
    from graphserver.core import Graph, State, TripHop
except ImportError:
    from core import Graph, State
from time import time as now
import traceback
import simplejson

import re
_rc = re.compile
from types import *
import cgi

class Servable:
    @classmethod
    def _urlpatterns(cls):
        ret = []
        
        for name in dir(cls):
            attr = getattr(cls, name)
            if type(attr) == UnboundMethodType and hasattr(attr, 'path') and hasattr(attr,'args'):
                ret.append( (re.compile(attr.path), attr, attr.args) )
                
        return ret
        
    def _usage(self, urlpatterns):
        ret = ["<?xml version='1.0'?><api>"]
        for ppath, pfunc, pargs in urlpatterns:
            ret.append("<method><path>%s</path><parameters>" % ppath.pattern)
            if pargs:
                for p in pargs:
                    ret.append("<param>%s</param>" %p)
            ret.append("</parameters></method>")
        ret.append("</api>")
        return "".join(ret)

    def wsgi_app(self):
        """returns a wsgi app which exposes this object as a webservice"""
        
        urlpatterns = self._urlpatterns()
        
        def myapp(environ, start_response):
            
            for ppath, pfunc, pargs in urlpatterns:
                if ppath.match(environ['PATH_INFO']):
                    args = {}
                    if pargs and environ['QUERY_STRING'] != "":
                        args = cgi.parse_qs(environ['QUERY_STRING'])
                        for k in args.keys():
                            args[k] = args[k][0]
                    try:
                        fargs = [args.get(parg) for parg in pargs]
                        r = pfunc(self,*fargs)
            
                        if hasattr(pfunc, 'mime'):
                            mime = pfunc.mime
                        else:
                            mime = 'text/xml'
                        content_length = len(r)
                        start_response('200 OK', [('Content-type', mime),('Content-Length', str(content_length))])
                        return [r]
                    except:
                        traceback.print_exc()
                        start_response('500 Internal Error', [('Content-type', 'text/plain')])
                        return ["Something went wrong"]
            # no match:
            start_response('200 OK', [('Content-type', 'text/xml')])
            return [self._usage(urlpatterns)]
            
        return myapp

class Engine(object, Servable):
    """ Provides a high level API to graph functions, outputing data to XML."""

    def __init__(self, graph):
        self.gg = graph
        
    def __del__(self):
        self.gg.destroy()

    @property
    def graph(self):
        return self.gg

    def _parse_init_state(self, numauthorities, time ):
        if time is None:
            time = int(now())
        else:
            time = int(time)
        
        return State(numauthorities, time)

    def _shortest_path_raw(self,dir_forward,doubleback,from_v,to_v,time,transfer_penalty=0):
        """returns (spt,vertices,edges). You need to destroy spt when you're done with the path"""
        if not self.gg.get_vertex(from_v) and self.gg.get_vertex(to_v):
            raise
            
        init_state = self._parse_init_state(self.gg.numauthorities, time)
        if transfer_penalty is None:
            transfer_penalty = 0
        else:
            transfer_penalty = int(transfer_penalty)
        
        if type(doubleback)==type(True):
            pass
        elif doubleback is None:
            doubleback = True
        else:
            doubleback = (doubleback.lower()=="true")
        
        if not dir_forward:
            spt = self.gg.shortest_path_tree_retro(from_v, to_v, init_state, transfer_penalty)
            if doubleback:
                origin = spt.get_vertex(from_v)
                if origin is not None:
                    departure_time = origin.payload.time
                    spt.destroy()
                    spt = self.gg.shortest_path_tree( from_v, to_v, State(self.gg.numauthorities, departure_time),transfer_penalty )
                    vertices, edges = spt.path(to_v)
                else:
                    spt.destroy()
                    spt, vertices, edges = None, None, None
            else:
                vertices, edges = spt.path_retro(from_v)
        else:
            spt = self.gg.shortest_path_tree(from_v, to_v, init_state, transfer_penalty)
            if doubleback:
                dest = spt.get_vertex(to_v)
                if dest is not None:
                    arrival_time = dest.payload.time
                    spt.destroy()
                    spt = self.gg.shortest_path_tree_retro( from_v, to_v, State(self.gg.numauthorities, arrival_time),transfer_penalty )
                    vertices, edges = spt.path_retro(from_v)
                else:
                    spt.destroy()
                    spt, vertices, edges = None, None, None
            else:
                vertices, edges = spt.path(to_v)
                
        return spt, vertices, edges
        

    def _shortest_path_general(self,dir_forward,doubleback,from_v,to_v,time,transfer_penalty=0):
        spt, vertices, edges = self._shortest_path_raw(dir_forward,doubleback,from_v,to_v,time,transfer_penalty)
                
        ret = ["<?xml version='1.0'?><route>"]
        if vertices is None:
            ret.append("<error>destination unreachable</error>")
        else:
            for i in range(len(edges)):
                ret.append(vertices[i].to_xml())
                ret.append(edges[i].to_xml())
            ret.append(vertices[-1].to_xml())
        ret.append("</route>")
        spt.destroy()
        return "".join(ret)
            
    def shortest_path(self, from_v, to_v, time,doubleback="true",transfer_penalty=0):
        return self._shortest_path_general( True, doubleback, from_v, to_v, time, transfer_penalty )
    shortest_path.path = r'/shortest_path$'
    shortest_path.args    = ('from','to','time','doubleback','tp')
            
    def shortest_path_retro(self, from_v, to_v, time,doubleback="true",transfer_penalty=0):
        return self._shortest_path_general( False, doubleback, from_v, to_v, time, transfer_penalty )
    shortest_path_retro.path = r'/shortest_path_retro$'
    shortest_path_retro.args = ('from','to','time','doubleback','tp')

    def all_vertex_labels(self):
        ret = ["<?xml version='1.0'?>"]
        ret.append("<labels>")
        for v in self.gg.vertices:
            ret.append("<label>%s</label>" % v.label)
        ret.append("</labels>")
        return "".join(ret)
    all_vertex_labels.path = r'/vertices'
    all_vertex_labels.args = ()

    def outgoing_edges(self, label):
        ret = ["<?xml version='1.0'?>"]
        
        v = self.gg.get_vertex(label)
        
        ret.append("<edges>")
        for e in v.outgoing:
            ret.append("<edge>")
            ret.append("<dest>%s</dest>" % e.to_v.to_xml())
            ret.append("<payload>%s</payload>" %e.payload.to_xml())
            ret.append("</edge>")
        ret.append("</edges>")
        return "".join(ret)
    outgoing_edges.path = r'/vertex/outgoing$'
    outgoing_edges.args = ('label',)

    def walk_edges_general(self, forward_dir, label, time):
        vertex = self.gg.get_vertex( label )
        init_state = self._parse_init_state(self.gg.numauthorities, time)

        ret = ["<?xml version='1.0'?>"]
        ret.append("<vertex>")
        ret.append(init_state.to_xml())
        ret.append("<outgoing_edges>")
        for edge in vertex.outgoing:
            ret.append("<edge>")
            ret.append("<destination label='%s'>" % edge.to_v.label)
            if forward_dir:
                if hasattr( edge.payload, 'collapse' ):
                    collapsed = edge.payload.collapse( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    ret.append(collapsed.walk( init_state ).to_xml())
                else:
                    ret.append("<state/>")
            else:
                if hasattr( edge.payload, 'collapse_back' ):
                    collapsed = edge.payload.collapse_back( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    ret.append(collapsed.walk_back( init_state ).to_xml())
                else:
                    ret.append("<state/>")
            ret.append("</destination>")
            if collapsed:
                ret.append("<payload>%s</payload>" % collapsed.to_xml())
            else:
                ret.append("<payload/>")
            ret.append("</edge>")
        ret.append("</outgoing_edges>")
        ret.append("</vertex>")
        return "".join(ret)
        
    def walk_edges(self, label, time):
        return self.walk_edges_general( True, label, time )
    walk_edges.path = r'/vertex/walk$'
    walk_edges.args = ('label', 'time')
        
    def walk_edges_retro(self, label, time):
        return self.walk_edges_general( False, label, time )
    walk_edges_retro.path = r'/vertex/walk_retro$'
    walk_edges_retro.args = ('label', 'time')
        
    def collapse_edges(self, label, time):
        vertex = self.gg.get_vertex( label )
        init_state = self._parse_init_state(self.gg.numauthorities, time)
        ret = ["<?xml version='1.0'?>"]
        ret.append("<vertex>")
        ret.append(init_state.to_xml())
        ret.append("<outgoing_edges>")
        for edge in vertex.outgoing:
            ret.append("<edge>")
            ret.append("<destination label='%s' />" % edge.to_v.label)
            collapsed = edge.payload.collapse( init_state )
            if collapsed:
                ret.append("<payload>%s</payload>" % collapsed.to_xml())
            else:
                ret.append("<payload/>")
            ret.append("</edge>")
        ret.append("</outgoing_edges>")
        ret.append("</vertex>")
        return "".join(ret)
    collapse_edges.path = r'/vertex/outgoing/collapsed$'
    collapse_edges.args = ('label', 'time')

class Action:
    action = "action"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return True
    
    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s -> %s"%(str(lastedge),str(nextedge)),None,None)
    
class Board(Action):
    action="board"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return nextedge is not None and nextedge.payload.__class__==TripHop and (lastedge is None or lastedge.payload.__class__!=TripHop or lastedge.payload.trip_id!=nextedge.payload.trip_id)
        
    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s at %s"%(nextedge.payload.trip_id, vertex.label),TripHop._daysecs_to_str(nextedge.payload.depart),None)
        
class Pass(Action):
    action="pass"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return verbose and lastedge is not None and nextedge is not None and lastedge.payload.__class__==TripHop and nextedge.payload.__class__==TripHop and lastedge.payload.trip_id==nextedge.payload.trip_id

    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,vertex.label,TripHop._daysecs_to_str(lastedge.payload.arrive),None)

class Alight(Action):
    action="alight"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return lastedge is not None and lastedge.payload.__class__==TripHop and (nextedge is None or nextedge.payload.__class__!=TripHop or lastedge.payload.trip_id!=nextedge.payload.trip_id)

    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s at %s"%(lastedge.payload.trip_id, vertex.label),TripHop._daysecs_to_str(lastedge.payload.arrive),None)

class TripPlanEngine(Engine):
    def __init__(self, gg, action_handlers=(Alight,Board,Pass)):
        Engine.__init__(self, gg)
        self.action_handlers = action_handlers
    
    def _actions_from_path(self, vertices, edges, verbose=False):
        actions = []
        
        for vertex,lastedge,nextedge in zip(vertices, [None]+edges, edges+[None]):
            for handler in self.action_handlers:
                if handler.applies(vertex,lastedge, nextedge, verbose):
                    actions.append( handler.describe( vertex, lastedge, nextedge ) )
                    
        return actions
    
    def trip_plan(self,from_v,to_v,time,verbose):
        verbose=verbose.lower()=="true"
        if time is None:
            time=int(now())
        
        spt, vertices, edges = self._shortest_path_raw( True, False, from_v, to_v, time, transfer_penalty=1 )
        
        actions = self._actions_from_path(vertices,edges,verbose)

        ret = ["<?xml version='1.0'?>"]
        ret.append( "<trip_plan>" )
        for action,location,when,latlon in actions:
            ret.append( "<action what='%s' where='%s' when='%s'/>"%(action,location,when) )
        ret.append( "</trip_plan>" )
        
        spt.destroy()
        
        return "".join(ret)
    trip_plan.path = r'/trip_plan$'
    trip_plan.args = ('from','to','time','verbose')
    
    def trip_plan_json(self,from_v,to_v,time,verbose):
        verbose=verbose.lower()=="true"
        if time is None:
            time=int(now())
            
        spt, vertices, edges = self._shortest_path_raw( True, False, from_v, to_v, time, transfer_penalty=1 )
        actions = self._actions_from_path(vertices,edges,verbose)
        ret = simplejson.dumps(actions)
        spt.destroy()
        
        return ret
    trip_plan_json.path = r'/trip_plan/json'
    trip_plan_json.args = ('from','to','time','verbose')
    trip_plan_json.mime = "text/plain"

def _test():
    #from pygs.engine import *
    e = Engine()
    
