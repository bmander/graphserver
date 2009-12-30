from graphserver.graphdb import GraphDatabase
from graphserver.ext.osm.profiledb import ProfileDB
from graphserver.core import Street

def cons(ary):
    for i in range(len(ary)-1):
        yield (ary[i], ary[i+1])

def get_rise_and_fall( profile ):
    rise=0
    fall=0
    
    if profile is not None:
        for (d1, e1), (d2, e2) in cons(profile):
            diff = e2-e1
            if diff>0:
                rise += diff
            elif diff<0:
                fall -= diff
            
    return rise, fall

from sys import argv

def main():
    if len(argv) < 2:
        print "usage: python import_ned.py graphdb_filename profiledb_filename"
        return
        
    graphdb_filename = argv[1]
    profiledb_filename = argv[2]
        
    gdb = GraphDatabase( graphdb_filename )
    profiledb = ProfileDB( profiledb_filename )
    
    n = gdb.num_edges()

    for i, (oid, vertex1, vertex2, edge) in enumerate( list(gdb.all_edges(include_oid=True)) ):
        if i%500==0: print "%s/%s"%(i,n)
        
        if isinstance( edge, Street ):
            rise, fall = get_rise_and_fall( profiledb.get( edge.name ) )
            edge.rise = rise
            edge.fall = fall
            
            gdb.remove_edge( oid )
            gdb.add_edge( vertex1, vertex2, edge )
            
if __name__=='__main__':
    main()
            

