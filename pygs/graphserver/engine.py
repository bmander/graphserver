try:
    from graphserver.core import Graph, State, Headway, Street, WalkOptions
except ImportError:
    from core import Graph, State, Headway, Street, WalkOptions
from time import time as now

try:
    import simplejson
except ImportError:
    import json as simplejson #support for python2.6

from servable import Servable

class Engine(object, Servable):
    """ Provides a high level API to graph functions, outputing data to XML."""

    def __init__(self, graph):
        self.gg = graph
        
    def __del__(self):
        self.gg.destroy()

    @property
    def _graph(self):
        return self.gg

    def _parse_init_state(self, numagencies, time ):
        if time is None:
            time = int(now())
        else:
            time = int(time)
        
        return State(numagencies, time)

    def _shortest_path_raw(self,dir_forward,from_v,to_v,time,doubleback=True,tp=0):
        """returns (spt,vertices,edges). You need to destroy spt when you're done with the path"""
        
        if not self.gg.get_vertex(from_v):
        	raise Exception( "Graph does not contain origin vertex, with label '%s'"%from_v )
        
        if not self.gg.get_vertex(to_v):
            raise Exception( "Graph does not contain destination vertex, with label '%s'"%to_v )
        
        tp = int(tp)
        doubleback = (str(doubleback).lower()=="true")
        
        init_state = self._parse_init_state(self.gg.numagencies, time)
        
        if not dir_forward:
            spt = self.gg.shortest_path_tree_retro(from_v, to_v, init_state, tp)
            if doubleback:
                origin = spt.get_vertex(from_v)
                if origin is not None:
                    departure_time = origin.payload.time
                    spt.destroy()
                    spt = self.gg.shortest_path_tree( from_v, to_v, State(self.gg.numagencies, departure_time),tp )
                    vertices, edges = spt.path(to_v)
                else:
                    spt.destroy()
                    spt, vertices, edges = None, None, None
            else:
                vertices, edges = spt.path_retro(from_v)
        else:
            spt = self.gg.shortest_path_tree(from_v, to_v, init_state, tp)
            if doubleback:
                dest = spt.get_vertex(to_v)
                if dest is not None:
                    arrival_time = dest.payload.time
                    spt.destroy()
                    spt = self.gg.shortest_path_tree_retro( from_v, to_v, State(self.gg.numagencies, arrival_time),tp )
                    vertices, edges = spt.path_retro(from_v)
                else:
                    spt.destroy()
                    spt, vertices, edges = None, None, None
            else:
                vertices, edges = spt.path(to_v)
                
        if vertices is None or edges is None:
        	raise Exception( "Path could not be found from %s to %s"%(from_v, to_v) )
                
        return spt, vertices, edges
        

    def _shortest_path_general(self,dir_forward,from_v,to_v,time,doubleback,tp=0):
        spt, vertices, edges = self._shortest_path_raw(dir_forward,from_v,to_v,time,doubleback,tp)
                
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
            
    def shortest_path(self, from_v, to_v, time,doubleback="true",tp=0):
        return self._shortest_path_general( True, from_v, to_v, time, doubleback, tp )
    shortest_path.mime = "text/xml"
            
    def shortest_path_retro(self, from_v, to_v, time,doubleback="true",tp=0):
        return self._shortest_path_general( False, from_v, to_v, time, doubleback, tp )
    shortest_path_retro.mime = "text/xml"

    def all_vertex_labels(self):
        ret = ["<?xml version='1.0'?>"]
        ret.append("<labels>")
        for v in self.gg.vertices:
            ret.append("<label>%s</label>" % v.label)
        ret.append("</labels>")
        return "".join(ret)
    all_vertex_labels.path = r'/vertices$'
    all_vertex_labels.mime = "text/xml"

    def outgoing_edges(self, label):
        ret = ["<?xml version='1.0'?>"]
        
        v = self.gg.get_vertex(label)
        
        if v is None:
            raise Exception( "The graph does not contain a vertex with label '%s'"%label )
        
        ret.append("<edges>")
        for e in v.outgoing:
            ret.append("<edge>")
            ret.append("<dest>%s</dest>" % e.to_v.to_xml())
            ret.append("<payload>%s</payload>" %e.payload.to_xml())
            ret.append("</edge>")
        ret.append("</edges>")
        return "".join(ret)
    outgoing_edges.path = r'/vertex/outgoing$'
    outgoing_edges.mime = "text/xml"

    def _walk_edges_general(self, forward_dir, label, time):
        vertex = self.gg.get_vertex( label )
        init_state = self._parse_init_state(self.gg.numagencies, time)

        dest_states = []
        for edge in vertex.outgoing:
            if forward_dir:
                if hasattr( edge.payload, 'collapse' ):
                    collapsed = edge.payload.collapse( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    wo = WalkOptions()
                    dest_states.append( (edge, collapsed, collapsed.walk( init_state,wo )) )
                    wo.destroy()
            else:
                if hasattr( edge.payload, 'collapse_back' ):
                    collapsed = edge.payload.collapse_back( init_state )
                else:
                    collapsed = edge.payload
                if collapsed:
                    wo = WalkOptions()
                    dest_states.append( (edge, collapsed, collapsed.walk_back( init_state,wo )) )
                    wo.destroy()
        
        def sort_states(x,y):
            if x[2] is None:
                return 1
            if y[2] is None:
                return -1
            else:
                return cmp(x[2].weight, y[2].weight)
        
        dest_states.sort(cmp=sort_states) #sort by weight of final state
        
        #====================

        ret = ["<?xml version='1.0'?>"]
        ret.append("<vertex>")
        ret.append(init_state.to_xml())
        ret.append("<outgoing_edges>")
        for edge, collapsed, sprime in dest_states:
            ret.append("<edge>")
            ret.append("<destination label='%s'>" % edge.to_v.label)
            if sprime:
                ret.append(sprime.to_xml())
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
        return self._walk_edges_general( True, label, time )
    walk_edges.path = r'/vertex/walk$'
    walk_edges.mime = "text/xml"
        
    def walk_edges_retro(self, label, time):
        return self._walk_edges_general( False, label, time )
    walk_edges_retro.path = r'/vertex/walk_retro$'
    walk_edges_retro.mime = "text.xml"
        
    def collapse_edges(self, label, time):
        vertex = self.gg.get_vertex( label )
        init_state = self._parse_init_state(self.gg.numagencies, time)
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
    collapse_edges.mime = "text/xml"
    
    def calendar_period(self,label,edge,time):
        edge = int(edge)
        time = int(time)
        
        vv = self.gg.get_vertex(label)
        
        ret = ["<?xml version='1.0'?>"]
        e = vv.outgoing[edge]
        cc = e.payload.calendar
        ret.append( str( cc.period_of_or_after( time ) ) )
            
        return "".join(ret)
    calendar_period.path = r'/calendar_period'
    calendar_period.mime = "text/xml"
    
    def calendar(self,label,edge):
        edge = int(edge)
        
        vv = self.gg.get_vertex(label)
        
        return vv.outgoing[edge].payload.calendar.to_xml()
    calendar.path = "/calendar$"
    calendar.mime = "text/xml"

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
        
class BoardHeadway(Action):
    action="board"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return nextedge is not None and nextedge.payload.__class__==Headway and (lastedge is None or lastedge.payload.__class__!=Headway or lastedge.payload.trip_id!=nextedge.payload.trip_id)
        
    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s at %s"%(nextedge.payload.trip_id, vertex.label),"about %d+%d"%(vertex.payload.time,nextedge.payload.wait_period),None)
        
class Pass(Action):
    action="pass"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return verbose and lastedge is not None and nextedge is not None and (lastedge.payload.__class__==TripHop or lastedge.payload.__class__==Headway) and (nextedge.payload.__class__==TripHop or nextedge.payload.__class__==Headway) and lastedge.payload.trip_id==nextedge.payload.trip_id

    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        #displays different time format for Headway and TripHop; a crude patch so Headway lastedges don't crash things
        strt = lastedge.payload.__class__ == Headway and str(vertex.payload.time) or TripHop._daysecs_to_str(lastedge.payload.arrive)
        return (cls.action,vertex.label,strt,None)

class Alight(Action):
    action="alight"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return lastedge is not None and lastedge.payload.__class__==TripHop and (nextedge is None or nextedge.payload.__class__!=TripHop or lastedge.payload.trip_id!=nextedge.payload.trip_id)

    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s at %s"%(lastedge.payload.trip_id, vertex.label),TripHop._daysecs_to_str(lastedge.payload.arrive),None)
        
class AlightHeadway(Action):
    action="alight"
    
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return lastedge is not None and lastedge.payload.__class__==Headway and (nextedge is None or nextedge.payload.__class__!=Headway or lastedge.payload.trip_id!=nextedge.payload.trip_id)

    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return (cls.action,"%s at %s"%(lastedge.payload.trip_id, vertex.label),"%d"%(vertex.payload.time),None)
        
class StartWalking(Action):
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return nextedge is not None and nextedge.payload.__class__==Street
        
    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return ("start walking", vertex.label, str(vertex.payload.time), None)
        
class FinishWalking(Action):
    @classmethod
    def applies(cls,vertex,lastedge,nextedge,verbose=False):
        return lastedge is not None and lastedge.payload.__class__==Street
        
    @classmethod
    def describe(cls,vertex,lastedge,nextedge):
        return ("finish walking", vertex.label, str(vertex.payload.time), None)

class TripPlanEngine(Engine):
    def __init__(self, gg, action_handlers=(AlightHeadway,Alight,BoardHeadway,Board,Pass)):
        Engine.__init__(self, gg)
        self.action_handlers = action_handlers
    
    def _actions_from_path(self, vertices, edges, verbose=False):
        actions = []
        
        for vertex,lastedge,nextedge in zip(vertices, [None]+edges, edges+[None]):
            for handler in self.action_handlers:
                if handler.applies(vertex,lastedge, nextedge, verbose):
                    actions.append( handler.describe( vertex, lastedge, nextedge ) )
                    
        return actions
    
    def trip_plan(self,from_v,to_v,time=None,verbose=False,forward=True):
        if time is None:
            time=int(now())
        
        spt, vertices, edges = self._shortest_path_raw( forward, from_v, to_v, time, doubleback=False, tp=1 )
        
        actions = self._actions_from_path(vertices,edges,verbose)

        ret = ["<?xml version='1.0'?>"]
        ret.append( "<trip_plan>" )
        for action,location,when,latlon in actions:
            ret.append( "<action what=\"%s\" where=\"%s\" when=\"%s\"/>"%(action,location,when) )
        ret.append( "</trip_plan>" )
        
        spt.destroy()
        
        return "".join(ret)
    trip_plan.mime = "text/xml"
    
    def trip_plan_json(self,from_v,to_v,time=None,verbose=False,forward=True):
        if time is None:
            time=int(now())
            
        spt, vertices, edges = self._shortest_path_raw( forward, from_v, to_v, time, doubleback=False, tp=1 )
        
        actions = self._actions_from_path(vertices,edges,verbose)
        ret = simplejson.dumps(actions)
        spt.destroy()
        
        return ret
    trip_plan_json.path = r'/trip_plan/json'
    trip_plan_json.mime = "text/plain"

def _test():
    #from pygs.engine import *
    e = Engine()
    
