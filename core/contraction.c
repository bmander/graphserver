#include "graph.h"
#include "contraction.h"
#include "fibheap.h"
#define TRUE 1
#define FALSE 0



Path* pathNew( int n, long length ) {
  Path *this = (Path*)malloc(sizeof(Path));
  this->n = n;
  this->payloads = (EdgePayload**)malloc(n*sizeof(EdgePayload*));
  this->length = length;

  return this;
}

Path* pathNewHollow( long length ) {
    Path *this = (Path*)malloc(sizeof(Path));
    this->n = 0;
    this->payloads = NULL;
    this->length = length;
    
    return this;
}

int pathLength( Path* this ) {
    if(!this) {
        return INFINITY;
    }
    
    return this->length;
}

Path* pathCombine( Path* a, Path* b ) {
    Path* ret = pathNew( a->n+b->n, a->length+b->length );
    int i;
    for(i=0; i<a->n; i++) {
        ret->payloads[i]=a->payloads[i];
    }
    for(i=0; i<b->n; i++) {
        ret->payloads[a->n+i]=b->payloads[i];
    }
    return ret;
}

void pathDestroy( Path* this ) {
    if(!this) return;
    
    free( this->payloads );
    free( this );
}
    
Path* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path )  {
    if( strcmp( from_v_label, to_v_label ) == 0 ) {
        return NULL;
    }
    
    State *dummy = stateNew(0,0);
    ShortestPathTree* spt = gShortestPathTree( gg, from_v_label, to_v_label, dummy, wo, INFINITY, INFINITY, weightlimit );
    
    SPTVertex* curs = sptGetVertex( spt, to_v_label );
    
    if(!curs) {
        sptDestroy( spt );
        return NULL;
    }
    
    Path* ret;
    
    if( return_full_path ) {
        // get path length
        int pathlength = 0;
        Edge *currparent = sptvGetParent( curs );
        while(currparent) {
            pathlength++;
            currparent = sptvGetParent( (SPTVertex*)currparent->from );
        }
        
        ret = pathNew( pathlength, curs->state->weight );
        int i;
        for(i=pathlength-1; i>=0; i--) {
            Edge* parent = sptvGetParent( curs ) ;
            ret->payloads[i] = parent->payload;
            curs = (SPTVertex*)parent->from;
        }
    } else {
        ret = pathNewHollow( curs->state->weight );
    }
    
    sptDestroy( spt );
    
    return ret;
}

Path** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) {
    long n_us, n_ws;
    int i,j;
    
    // GET VERTICES TO INCLUDE IN THE ALL-PAIRS SEARCH
    State *dummy = stateNew( 0, 10000 );
    ShortestPathTree* sptin = gShortestPathTreeRetro( gg, "bogus", vv->label, dummy, wo, 0, search_limit, INFINITY );
    SPTVertex** us = sptVertices( sptin, &n_us );
    State *dummy2 = stateNew( 0, 0 );
    ShortestPathTree* sptout = gShortestPathTree( gg, vv->label, "bogus", dummy2, wo, INFINITY, search_limit, INFINITY );
    SPTVertex** ws = sptVertices( sptout, &n_ws );

    // THE RETURN ARRAY CANNOT BE LARGER THAN len(u)*len(w) PATHS
    Path** ret = (Path**)malloc(n_us*n_ws*sizeof(Path*));
    int count = 0;
    
    // GET PATHS c(u,v) FROM ALL us TO v
    Path** cuv = (Path**)malloc(n_us*sizeof(Path*));
    for(i=0; i<n_us; i++) {
        cuv[i] = dist( gg, us[i]->label, vv->label, wo, INFINITY, TRUE );
    }
    
    // GET PATHS c(v,w) FROM v to ALL ws, FINDING THE MAX c(v,w)
    Path** cvw = (Path**)malloc(n_ws*sizeof(Path*));
    int max_cvw = -INFINITY;
    for(i=0; i<n_ws; i++) {
        cvw[i] = dist( gg, vv->label, ws[i]->label, wo, INFINITY, TRUE );
        if( cvw[i] && cvw[i]->length > max_cvw ) {
            max_cvw = cvw[i]->length;
        }
    }
    
    // FOR ALL us AND ws, SEE IF THERE IS A PATH FROM u TO w IGNORING v THAT IS SHORTER THAN THE PATH THROUGH v
    gSetVertexEnabled( gg, vv->label, 0 );
    
    //FOR EACH U
    for(i=0; i<n_us; i++) {
        SPTVertex* u = us[i];
        
        //if the path c(u,v) is NULL, it means u==v; ignore
        if(cuv[i]) {
        
            int cuv_length = pathLength( cuv[i] );
            int weightlimit = cuv_length+max_cvw;
            
            //FOR EACH W
            for(j=0; j<n_ws; j++) {
                SPTVertex* w = ws[j];
                
                // the path c(v,w) must be non-NULL, and u!=w
                if( cvw[j] && strcmp(u->label,w->label)!=0 ) {
                    Path* duw = dist( gg, u->label, w->label, wo, weightlimit, FALSE);
                    
                    // IF THE PATH AROUND IS LONGER THAN THE PATH THROUGH, ADD THE PATH THROUGH TO THE SHORTCUTS
                    if( cuv_length+pathLength(cvw[j]) < pathLength(duw) ) {
                        Path* yld = pathCombine( cuv[i], cvw[i] );
                        ret[count] = yld;
                        count++;
                    }
                    
                    pathDestroy( duw );
                }
            }
        
        }
    }
    gSetVertexEnabled( gg, vv->label, 1 );
    
    for(i=0; i<n_us; i++) {
        pathDestroy( cuv[i] );
    }
    free( cuv );
    for(i=0; i<n_ws; i++) {
        pathDestroy( cvw[i] );
    }
    free( cvw );
    
    free( us );
    free( ws );
    
    sptDestroy( sptin );
    sptDestroy( sptout );
    
    *n = count;
    return ret;
}

void pqPush( fibheap *pq, Vertex* item, int priority ) {
    fibheap_insert( pq, priority, (void*)item );
}

Vertex* pqPop( fibheap *pq ) {
    return (Vertex*)fibheap_extract_min( pq );
}

int get_importance(int degree_in, int degree_out, int n_shortcuts) {
    int edge_difference = n_shortcuts - (degree_in+degree_out);
    return edge_difference;
}

fibheap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit ) {
    fibheap* pq = fibheap_new();

    long n;
    int i;
    Vertex** vertices = gVertices( gg, &n );
    for(i=0; i<n; i++) {
        Vertex* vv = vertices[i];
        printf( "%s %d/%ld\n", vv->label, i+1, n );
        int n_shortcuts;
        Path** shortcuts = get_shortcuts( gg, vv, wo, search_limit, &n_shortcuts );
        int imp = get_importance( vv->degree_in, vv->degree_out, n_shortcuts );
        pqPush( pq, vv, imp );
        int j;
        for(j=0; j<n_shortcuts; j++){
            pathDestroy( shortcuts[j] );
        }
        free( shortcuts );
    }
    free(vertices);
    return pq;
}

/*
//def get_contraction_heirarchies(gg, hoplimit=2, max_contract=None):
CH* get_contraction_heirarchies(Graph* gg) {
    fibheap* pq = fibheap_new();

    Graph* gup = gNew();
    Graph* gdown = gNew();
    
//    rolling_degree = 1.0
//    search_limit = 1
    
    i = 0
    while len(pq)>0:
        if max_contract and i == max_contract:
            break
        
        i += 1
        
        #print "--==--"
        #print "pq", pq
        prio, vertex = heapq.heappop( pq )
        rolling_degree = (rolling_degree*9+vertex.degree_out+vertex.degree_in)/11
        print "contract %d/%d"%(i,len(vertex_order)), vertex
        # make sure priority of current vertex
        while True:
            shortcuts = list(get_shortcuts( gg, vertex, 1, hoplimit ))
            #print "shortcuts", shortcuts
            new_prio = get_importance( vertex, shortcuts )
            if new_prio == prio:
                #print "fine"
                break
            else:
                #print "reevaluate"
                heapq.heappush( pq, (new_prio, vertex) )
                prio, vertex = heapq.heappop( pq )
                #print "new vertex", vertex
                
        vertex_order.append( vertex.label )
            
        # add shortcuts
        for payloads, from_v, to_v in shortcuts:
            # add shortcut
            shortcut_payload = concatenate_payloads( payloads )
            #print "add", shortcut_payload, from_v, to_v
            gg.add_edge( from_v, to_v, shortcut_payload )
            
        # move edges from gg to gup and gdown
        # vertices that are still in the graph are, by definition, of higher importance than the one
        # currently being plucked from the graph. Edges that go out are upward edges. Edges that are coming in
        # are downward edges.
        
        in_vert_counts = histogram( [ee.from_v.label for ee in vertex.incoming] )
        out_vert_counts = histogram( [ee.to_v.label for ee in vertex.outgoing] )
        for in_vert, count in in_vert_counts.items():
            if count > 1:
                print "WARNING: %d edges from %s to %s"%(count, in_vert, vertex.label)
        for out_vert, count in out_vert_counts.items():
            if count > 1:
                print "WARNING: %d edges from %s to %s"%(count, vertex.label, out_vert)
        
        #incoming, therefore downward
        gdown.add_vertex( vertex.label )
        for ee in vertex.incoming:
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
    
*/


