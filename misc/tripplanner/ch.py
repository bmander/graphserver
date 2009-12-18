from graphserver.graphdb import GraphDatabase
from graphserver.ext.osm.osmdb import OSMDB
from graphserver.core import State, WalkOptions, Graph, Street, Combination, EdgePayload, ContractionHierarchy

import sys
def make_native_ch(basename):
    gdb = GraphDatabase( basename+".gdb" )
    gg = gdb.incarnate()
    
    
    wo = WalkOptions()
    wo.hill_reluctance=20
    wo.walking_speed=4
    wo.walking_overage = 0
    wo.turn_penalty = 15

    ch = gg.get_contraction_hierarchies( wo )
            
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
    try:
        make_native_ch( sys.argv[1] )
    except IndexError:
        print "usage: python ch.py gdb_basename"
