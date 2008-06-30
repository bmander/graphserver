from graphserver.structures import Graph, State
import time

class XMLGraphEngine(object):

    @property
    def graph(self):
            return self.gg

    def parse_init_state(self, time=int(time.time())):
        return State(init_time)

    def __init__(self):
        gg = Graph()
        self.gg = gg

    def shortest_path(self, from_v, to_v, **init_state_params):
        ret = []
        if not self.gg.get_vertex(from_v) and self.gg.get_vertex(to_v):
            raise
        init_state = State(**init_state_params)
        #print init_state
        try:
            #Throws RuntimeError if no shortest path found.
            vertices, edges = self.gg.shortest_path(from_v, to_v, init_state) 
            ret = "<?xml version='1.0'?><route>"
            for i in range(len(edges)):
                ret += vertices[i].to_xml()
                ret += edge[i].to_xml()
                ret += vertices[-1].to_xml() + "</route>"
            return ret
        # TODO
        #except ArgumentError, e:
        #    raise "ERROR: Invalid parameters."
        except RuntimeError, e:
            raise "Couldn't find a shortest path from #{from} to #{to}"

    def all_vertex_labels(self):
      vlabels = "<?xml version='1.0'?>"
      vlabels += "<labels>"
      for v in self.gg.vertices:
        vlabels += "<label>%s</label>" % v.label
      vlabels += "</labels>"
      return vlabels

    def outgoing_edges(self, label):
        ret = "<?xml version='1.0'?>"
        ret += "<edges>"
        for v in self.gg.vertices:
            for e in v.outgoing:
                ret += "<edge>"
                ret += "<dest>%s</dest>" % e.to_v.to_xml()
                ret += "<payload>%s</payload>" %e.payload.to_xml()
                ret += "</edge>"
        ret += "</edges>"
        return ret

    def walk_edges(self, label, **statevars):
        vertex = self.gg.get_vertex( label )
        init_state = State(**statevars)

        ret = "<?xml version='1.0'?>"
        ret += "<vertex>"
        ret += init_state.to_xml()
        ret += "<outgoing_edges>"
        for edge in vertex.outgoing:
            ret += "<edge>"
            ret +=   "<destination label='%s'>" % edge.to_v.label
            collapsed = edge.payload.collapse( init_state )
            if collapsed:
                ret += collapsed.walk( init_state ).to_xml()
            else:
                ret += "<state/>"
        ret += "</destination>"
        if collapsed:
            ret += "<payload>%s</payload>" % collapsed.to_xml()
        else:
            ret += "<payload/>"
        ret += "</edge>"
        ret += "</outgoing_edges>"
        ret += "</vertex>"
        return ret

    def collapse_edges(self, label, **statevars):
        pass
    
def _test():
    #from graphserver.engine import *
    e = XMLGraphEngine()
    

"""
    @server.mount_proc( "/collapse_edges" ) do |request, response|
      vertex = @gg.get_vertex( request.query['label'] )
      init_state = parse_init_state( request )

      ret = ["<?xml version='1.0'?>"]
      ret += "<vertex>"
      ret += init_state.to_xml()
      ret += "<outgoing_edges>"
      vertex.each_outgoing do |edge|
        ret += "<edge>"
        ret += "<destination label='#{edge.to.label}' />"
        if collapsed = edge.payload.collapse( init_state ):
          ret += "<payload>#{collapsed.to_xml()}</payload>"
        else:
          ret += "<payload/>"

        ret += "</edge>"

      ret += "</outgoing_edges>"
      ret += "</vertex>"

      response.body = ret.join




def database_params= params(self):
    begin
      require 'postgres'
    rescue LoadError
      @db_params = nil
      raise


    begin
      #check if database connection works
      conn = PGconn.connect( params[:host],
                             params[:port],
                             params[:options],
                             params[:tty],
                             params[:dbname],
                             params[:login],
                             params[:password] )
      conn.close
    rescue PGError
      @db_params = nil
      raise


    @db_params = params
    return true


def connect_to_database(self):
    unless @db_params: return nil

    PGconn.connect( @db_params[:host],
                    @db_params[:port],
                    @db_params[:options],
                    @db_params[:tty],
                    @db_params[:dbname],
                    @db_params[:login],
                    @db_params[:password] )


#may return nil if postgres isn't loaded, or the connection params aren't set
def conn(self):
    #if @conn exists and is open
    if @conn and begin @conn.status rescue PGError false :
      return @conn
    else:
      return @conn = connect_to_database



"""