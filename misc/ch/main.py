from graphserver.graphdb import GraphDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.core import State, WalkOptions, Graph, Street, Combination, EdgePayload, ContractionHierarchy
import heapq
try:
    import json
except ImportError:
    import simplejson as json
import time

def histogram( ary ):
    ret = {}
    for x in ary:
        ret[x] = ret.get(x,0)+1
    return ret

def dist( gg, from_v, to_v, hoplimit=1000000, timelimit=10000000 ):
    spt = gg.shortest_path_tree( from_v, to_v, State(0,0), maxtime=timelimit, hoplimit=hoplimit )
    vertices, edges = spt.path( to_v )
    ret = ( [ee.payload for ee in edges], vertices[-1].state.weight) if vertices else (None, 100000000000)
    spt.destroy() #causes problems when referring to one of the edges' properties
    return ret

def concatenate_payloads( streets ):
    sum_name = ":".join( [street.name for street in streets] )
    sum_length = sum( [street.length for street in streets] )
    sum_rise = sum( [street.rise for street in streets] )
    sum_fall = sum( [street.fall for street in streets] )
    
    ret = Street( sum_name, sum_length, sum_rise, sum_fall )
    ret.way = streets[-1].way
    return ret

def get_shortcuts(Gprime, v, nearby_hoplimit, hoplimit):
        
    sptout = Gprime.shortest_path_tree( v.label, None, State(0,0), WalkOptions(), hoplimit=nearby_hoplimit )
    us = [vv.label for vv in sptout.vertices if vv.hop>0]
    sptout.destroy()
    sptin = Gprime.shortest_path_tree_retro( None, v.label, State(0,0), WalkOptions(), hoplimit=nearby_hoplimit )
    ws = [vv.label for vv in sptin.vertices if vv.hop>0]
    sptin.destroy()
    
    cuv = {}
    for u in us:
        cuv[u] = dist( Gprime, u, v.label )
        
    #print "cuv", cuv
    
    cvw = {}
    for w in ws:
        cvw[w] = dist( Gprime, v.label, w )
     
    try:
        maxcvw = max([x[1] for x in cvw.values()])
    except ValueError:
        maxcvw = 100000000
        
    #print "cvw", cvw
        
    Gprime.set_vertex_enabled( v.label, False )
    for u in us:
        for w in ws:
            if u != w:
                timelimit = cuv[u][1]+maxcvw
                
                duw = dist( Gprime, u, w, hoplimit, timelimit)
                
                #print u, w, duw
                #print cuv[u], cvw[w]
                
                if cuv[u][1]+cvw[w][1] < duw[1]:
                    yield (cuv[u][0]+cvw[w][0], u, w) #yield shortcut path
    Gprime.set_vertex_enabled( v.label, True )
    
def get_importance(v, shortcuts, neighbors_deleted=None):
    n_shortcuts = len(list(shortcuts))
    n_edges = v.degree_in+v.degree_out#len(v.incoming)+len(v.outgoing)
    
    edge_difference = n_shortcuts - n_edges
    
    #if neighbors_deleted:
    #    nd = neighbors_deleted.get( v.label, 0 )
    #else:
    #    nd = 0
    
    return edge_difference# + nd
    
def init_priority_queue( gg, hoplimit ):
    pq = []
    n = gg.size
    for i, vv in enumerate(gg.vertices):
        
        shortcuts = list(get_shortcuts( gg, vv, 1, hoplimit ))
        ed = get_importance(vv, shortcuts)
        print vv.label, "%d/%d prio:%d"%(i+1,n,ed)
        heapq.heappush( pq, (ed, vv) )
    return pq
    
def test_shortcuts():
    gg = Graph()
    gg.add_vertex( "1" )
    gg.add_vertex( "2" )
    gg.add_vertex( "3" )
    gg.add_edge( "1", "2", Street("12", 1) )
    gg.add_edge( "2", "3", Street("23", 1) )
    
    vv = gg.get_vertex( "1" )
    assert list(get_shortcuts( gg, vv)) == []
    
    vv = gg.get_vertex( "2" )
    assert list(get_shortcuts( gg, vv ))[0][1:3] == ('1', '3')
    
    vv = gg.get_vertex( "3" )
    assert list(get_shortcuts( gg, vv)) == []
    
    gg.set_vertex_enabled( "1", False )
    vv = gg.get_vertex( "2" )
    assert list( get_shortcuts( gg, vv ) ) == []

def get_contraction_hierarchies(gg, hoplimit=2, max_contract=None):
    print "initing priority queue"
    pq = init_priority_queue( gg, hoplimit )
    
    gup = Graph()
    gdown = Graph()
    vertex_order = []
    
    rolling_degree = 1.0
    search_limit = 1
    
    neighbors_deleted = {}
    
    nn = gg.size
    i = 0
    while len(pq)>0:
        if max_contract and i == max_contract:
            break
        
        i += 1
        
        #print "--==--"
        #print "pq", pq
        prio, vertex = heapq.heappop( pq )
        rolling_degree = (rolling_degree*9+vertex.degree_out+vertex.degree_in)/11
        
        #print "new vertex candidate", vertex.label
        
        # make sure priority of current vertex
        while True:
            shortcuts = list(get_shortcuts( gg, vertex, 1, hoplimit ))
            #print "shortcuts", shortcuts
            new_prio = get_importance( vertex, shortcuts, neighbors_deleted )
            if new_prio == prio:
                #print "fine"
                break
            else:
                print "updated priority %d != old priority %d, reevaluate"%(new_prio,prio)
                heapq.heappush( pq, (new_prio, vertex) )
                prio, vertex = heapq.heappop( pq )
                #print "new vertex candidate", vertex.label
                
        print "contract %d/%d %s (prio:%d) with %d shortcuts"%(i, nn, vertex.label, prio, len(shortcuts))
                
        vertex_order.append( vertex.label )
            
        # add shortcuts
        for payloads, from_v, to_v in shortcuts:
            # add shortcut
            shortcut_payload = concatenate_payloads( payloads )
            
            #s1 = shortcut_payload.walk( State(0,0), WalkOptions() )
            #print "add %s %s %s (%d long)"%(from_v, to_v, shortcut_payload.soul, s1.weight)
            
            gg.add_edge( from_v, to_v, shortcut_payload )
            
        # move edges from gg to gup and gdown
        # vertices that are still in the graph are, by definition, of higher importance than the one
        # currently being plucked from the graph. Edges that go out are upward edges. Edges that are coming in
        # are downward edges.
        
        #in_vert_counts = histogram( [ee.from_v.label for ee in vertex.incoming] )
        #out_vert_counts = histogram( [ee.to_v.label for ee in vertex.outgoing] )
        #for in_vert, count in in_vert_counts.items():
        #    if count > 1:
        #        print "WARNING: %d edges from %s to %s"%(count, in_vert, vertex.label)
        #for out_vert, count in out_vert_counts.items():
        #    if count > 1:
        #        print "WARNING: %d edges from %s to %s"%(count, vertex.label, out_vert)
        
        #incoming, therefore downward
        gdown.add_vertex( vertex.label )
        for ee in vertex.incoming:
            #neighbors_deleted[ee.from_v.label] = neighbors_deleted.get(ee.from_v.label,0)+1
            
            gdown.add_vertex( ee.from_v.label )
            gdown.add_edge( ee.from_v.label, ee.to_v.label, ee.payload )
            
        #outgoing, therefore upward
        gup.add_vertex( vertex.label )
        for ee in vertex.outgoing:
            gup.add_vertex( ee.to_v.label )
            gup.add_edge( ee.from_v.label, ee.to_v.label, ee.payload )
            
        # TODO inform neighbors their neighbor is being deleted
        gg.remove_vertex( vertex.label, free_edge_payloads=False )
        
    return gup, gdown, vertex_order

def add_bidir_street( gg, a, b, len ):
    gg.add_edge( a, b, Street( a+b, len ) )
    gg.add_edge( b, a, Street( b+a, len ) )

def print_graphs( gg, gup, gdown ):
    # inspect result
    print "INSPECT RESULT"
    print "gprime:"
    for vv in gg.vertices:
        print vv
    
    print "gup:"
    for vv in gup.vertices:
        print vv
        for ee in vv.outgoing:
            print "\t",ee.to_v
    
    print "gdown:"
    for vv in gdown.vertices:
        print vv
        for ee in vv.outgoing:
            print "\t",ee.to_v

def test_graph_contraction():

    gg = Graph()
    gg.add_vertex( "1" )
    gg.add_vertex( "2" )
    gg.add_vertex( "3" )
    gg.add_vertex( "4" )
    gg.add_edge( "1", "2", Street("12", 1) )
    gg.add_edge( "2", "3", Street("23", 1) )
    gg.add_edge( "3", "2", Street("32", 1) )
    gg.add_edge( "2", "1", Street("21", 1) )
    gg.add_edge( "3", "4", Street("34", 1) )
    gg.add_edge( "4", "3", Street("43", 1) )

    gup, gdown = get_contraction_hierarchies( gg )

    print_graphs( gg, gup, gdown )
            
    gg = Graph()
    gg.add_vertices( ('1', '2', '3', '4', '5', '6', '7', '8', '9') )
    add_bidir_street( gg, '1', '2', 1 )
    add_bidir_street( gg, '2', '3', 1 )
    add_bidir_street( gg, '4', '5', 1 )
    add_bidir_street( gg, '5', '6', 1 )
    add_bidir_street( gg, '7', '8', 1 )
    add_bidir_street( gg, '8', '9', 1 )
    add_bidir_street( gg, '1', '4', 1 )
    add_bidir_street( gg, '4', '7', 1 )
    add_bidir_street( gg, '2', '5', 1 )
    add_bidir_street( gg, '5', '8', 1 )
    add_bidir_street( gg, '3', '6', 1 )
    add_bidir_street( gg, '6', '9', 1 )
    
    gup, gdown = get_contraction_hierarchies( gg )

    print_graphs( gg, gup, gdown )
    
    gg = Graph()
    gg.add_vertex( "red" )
    gg.add_vertex( "aqua" )
    gg.add_vertex( "green" )
    gg.add_vertex( "yellow" )
    gg.add_vertex( "orange" )
    add_bidir_street( gg, "red", "aqua", 1 )
    add_bidir_street( gg, "aqua", "yellow", 1 )
    add_bidir_street( gg, "yellow", "orange", 1 ) 
    add_bidir_street( gg, "aqua", "green", 1 )
    add_bidir_street( gg, "orange", "green", 1 )
    
    gup, gdown = get_contraction_hierarchies( gg )
    
    print_graphs( gg, gup, gdown )

from prender import processing

def render_ch(gg, vertex_order, osmdb, vertex=-1):
    fp = open( "../sptviz2/data/ch.spt", "w" )
        
    for orig_level, vertex_label in list(enumerate(vertex_order)):
        #print orig_level, vertex_label
        vertex = gg.get_vertex( vertex_label )
        
        if vertex is not None:

            for ee in vertex.outgoing:
                if ee.to_v.label in vertex_order:
                    dest_level = vertex_order.index( ee.to_v.label )
                else:
                    dest_level = 0
                #print dest_level, ee.to_v.label
                
                fp.write( "OSMStreet,%s,%s,"%(ee.from_v.label, ee.to_v.label) )
                subedge_ids = ee.payload.name.split(":")
                first_subedge = osmdb.edge(subedge_ids[0])
                subgeoms = []
                
                #make sure the first edge is pointed in the right direction
                if "osm-%s"%first_subedge[2]==ee.from_v.label:
                    subgeoms.extend( first_subedge[5] )
                else:
                    subgeoms.extend( reversed(first_subedge[5]) )
                
                #add all other subedges to geom
                for subedge in subedge_ids[1:]:
                    subgeom = osmdb.edge(subedge)[5]
                    if len(subgeoms)>0 and subgeoms[-1]==subgeom[0]:
                        subgeoms.extend( subgeom[1:] )
                    else:
                        subgeoms.extend( list(reversed(subgeom))[1:] )
                        
                slanted_geoms = []
                for j, (x,y) in enumerate(subgeoms):
                    slanted_geoms.append( (x,y,orig_level+((dest_level-orig_level)/float(len(subgeoms)-1))*j) )
                    
                #print slanted_geoms
                
                line = ",".join( ["%f,%f,%f"%(x,y,imp) for x,y,imp in slanted_geoms] )
                fp.write( line )
                fp.write( "\n" )

    fp.close()
    
def render_graph(gg, osmdb):
    fp = open( "../sptviz2/data/ch.spt", "w" )
        
    for vertex in gg.vertices:
    
            for ee in vertex.outgoing:
                
                fp.write( "OSMStreet,%s,%s,"%(ee.from_v.label, ee.to_v.label) )
                subedge_ids = ee.payload.name.split(":")
                first_subedge = osmdb.edge(subedge_ids[0])
                subgeoms = []
                
                #make sure the first edge is pointed in the right direction
                if "osm-%s"%first_subedge[2]==ee.from_v.label:
                    subgeoms.extend( first_subedge[5] )
                else:
                    subgeoms.extend( reversed(first_subedge[5]) )
                
                #add all other subedges to geom
                for subedge in subedge_ids[1:]:
                    subgeom = osmdb.edge(subedge)[5]
                    if len(subgeoms)>0 and subgeoms[-1]==subgeom[0]:
                        subgeoms.extend( subgeom[1:] )
                    else:
                        subgeoms.extend( list(reversed(subgeom))[1:] )
                
                line = ",".join( ["%f,%f,0.0"%(x,y) for x,y in subgeoms] )
                fp.write( line )
                fp.write( "\n" )

    fp.close()

def gdb_to_ch_gdb(basename, max_contract=None):
    """create contraction hierarchy from graph database, and store the result 
    up-graph and down-graph in graph databases"""
    
    # reincarnate database
    print "reincarnating databases"
    gdb = GraphDatabase( basename+".gdb" )
    gg = gdb.incarnate()
    
    # get contraction hierarchies
    print "contracting graph"
    t0 = time.time()
    gup, gdown, vertex_order = get_contraction_hierarchies( gg, hoplimit=100000, max_contract=max_contract )
    print time.time()-t0
    
    # dump CHs to graph databases
    gdbup = GraphDatabase( basename+".up.gdb", overwrite=True )
    gdbup.populate( gup )
    gdbdown = GraphDatabase( basename+".down.gdb", overwrite=True )
    gdbdown.populate( gdown )
    fp = open( basename+".vorder", "w" )
    fp.write( json.dumps( vertex_order ) )
    gdb = GraphDatabase( basename+".remainder.gdb", overwrite=True )
    gdb.populate( gg )
    
def reincarnate_ch(basename):
    gdbup = GraphDatabase( basename+".up.gdb" )
    gup = gdbup.incarnate()
    gdbdown = GraphDatabase( basename+".down.gdb" )
    gdown = gdbdown.incarnate()
    fp = open( basename+".vorder", "r" )
    vertex_order = json.loads( fp.read() )
    fp.close()
    
    return gup, gdown, vertex_order

def test_path(basename):
    # pick a couple points to test
    origin = "osm-53218388"
    dest = "osm-130167088"
    
    wo = WalkOptions()
    
    gdb = GraphDatabase( basename+".remainder.gdb" )
    remaindergg = gdb.incarnate()
    #spt = gg.shortest_path_tree( origin, dest, State(0,0), wo )
    #print spt.get_vertex( dest ).state.weight
    #vvs, ees = spt.path( dest )
    #print [ee.payload.name for ee in ees]
    
    gup, gdown, vertex_order = reincarnate_ch( basename )
    osmdb = OSMDB( basename+".osmdb" )
    
    # get SPTs on up graph and down graph
    #print "SPT up"
    #sptup = gup.shortest_path_tree( origin, None, State(0,0), wo )
    #print "SPT down"
    #sptdown = gdown.shortest_path_tree_retro( None, dest, State(0,100000), wo )

    render_ch( gup, vertex_order, osmdb)
    
    #meetpoints = []
    #for vvup in sptup.vertices:
    #    vvdown = sptdown.get_vertex( vvup.label )
    #    if vvdown:
    #        meetpoints.append( ( vvup.label, vvup.state.weight+vvdown.state.weight ) )
    #print meetpoints
    #meetpoint = min(meetpoints, key=lambda x:x[1])
    #print "meetpoint", meetpoint
    #vvup, edgeup = sptup.path( meetpoint[0] )
    #vvdown, edgedown = sptdown.path( meetpoint[0] )
    # 
    #print [edge.payload.name for edge in edgeup + list(reversed( edgedown ))]
    #
    #
    # 
    #sptup.destroy()
    #sptdown.destroy()
    
    """
    print vertex_order.index( "osm-53139152" )
    
    vv = gup.get_vertex( "osm-53139152" )
    print vv
    print "out"
    for ee in vv.outgoing:
        print "\t", ee.to_v, ee
    print "in"
    for ee in vv.incoming:
        print "\t", ee.from_v, ee
    vv =  gdown.get_vertex( "osm-53139152" )
    print vv
    print "out"
    for ee in vv.outgoing:
        print "\t", ee.to_v, ee
    print "in"
    for ee in vv.incoming:
        print "\t", ee.from_v, ee
    
    
    for vv in sptup.vertices:
        print vv.label
        print vv.payload.weight
    print "--==--"
    for vv in sptdown.vertices:
        print vv.label
        print vv.payload.weight
    """

def osmdb_to_csv(basename, csvname):
    osmdb = OSMDB( basename+".osmdb" )
    
    fp = open( csvname, "w" )
    
    for edge_id, parent_id, from_id, to_id, len, geom, tags in osmdb.edges():
        fp.write( ",".join([str(x) for x in (edge_id, from_id, to_id, len)])+"\n" )
            
    fp.close()

import sys
def make_native_ch(basename):
    gdb = GraphDatabase( basename+".gdb" )
    gg = gdb.incarnate()
    
    ch = gg.get_contraction_hierarchies( WalkOptions() )
            
    chdowndb = GraphDatabase( basename+".down.gdb", overwrite=True )
    chdowndb.populate( ch.downgraph, reporter=sys.stdout )
    
    chupdb = GraphDatabase( basename+".up.gdb", overwrite=True )
    chupdb.populate( ch.upgraph, reporter=sys.stdout )

def reincarnate_chdbs(basename):
    chdowndb = GraphDatabase( basename+".down.gdb" )
    chupdb = GraphDatabase( basename+".up.gdb" )
    
    upgg = chupdb.incarnate()
    downgg = chdowndb.incarnate()
    
    return ContractionHierarchy(upgg, downgg)
    
    
    
if __name__ == '__main__':
    #osmdb_to_csv( "northseattle", "northseattle.csv" )
    
    #gdb_to_ch_gdb("northseattle", None)
    
    #test_path( "northseattle" )
    
    #make_native_ch( "seattle" )
    ch = reincarnate_chdbs( "seattle" )
    print ch.shortest_path( "osm-53144830", "osm-53092202", State(0,0), WalkOptions() )

#for vertex in gg.vertices:
#    shortcuts = list(get_shortcuts( gg, vertex ))
#    for shortcut in shortcuts:
#        print shortcut
#        shortcut_payload = concatenate_payloads( shortcut[0] )
#        shortcut_origin = shortcut[1]
#        shortcut_dest = shortcut[2]
#        print shortcut_origin
#        print shortcut_dest
#        print shortcut_payload
#        gg.add_edge( shortcut_origin, shortcut_dest, shortcut_payload )
