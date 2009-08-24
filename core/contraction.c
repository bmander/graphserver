#include "graph.h"
#include "contraction.h"
//#include "fibheap.h"
#include "heap.h"
#define TRUE 1
#define FALSE 0

CH* chNew(Graph *up, Graph *down) {
    CH* ret = (CH*)malloc(sizeof(Path));
    ret->up = up;
    ret->down = down;
    return ret;
}

Graph* chUpGraph( CH* this ) {
    return this->up;
}

Graph* chDownGraph( CH* this ) {
    return this->down;
}

void chDestroy( CH* this ) {
    free( this );
}

Path* pathNew( int n, long length ) {
  Path *this = (Path*)malloc(sizeof(Path));
  this->n = n;
  this->payloads = (EdgePayload**)malloc(n*sizeof(EdgePayload*));
  this->length = length;

  return this;
}

void pathPrint( Path* this ) {
  printf( "Path %d segs from %s to %s\n", this->n, this->fromv->label, this->tov->label );
}

Path* pathNewHollow( long length ) {
    Path *this = (Path*)malloc(sizeof(Path));
    this->n = 0;
    this->payloads = NULL;
    this->fromv = NULL;
    this->tov = NULL;
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
    ret->fromv = a->fromv;
    ret->tov = b->tov;
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

Combination* pathToEdgePayload( Path* this ) {
    Combination* ret = comboNew( this->n );
    int i;
    for(i=0; i<this->n; i++) {
        comboAdd( ret, this->payloads[i] );
    }
    return ret;
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
        if(cuv[i]) {
          cuv[i]->fromv = us[i]->mirror;
          cuv[i]->tov = vv;
        }
    }
    
    // GET PATHS c(v,w) FROM v to ALL ws, FINDING THE MAX c(v,w)
    Path** cvw = (Path**)malloc(n_ws*sizeof(Path*));
    int max_cvw = -INFINITY;
    for(i=0; i<n_ws; i++) {
        cvw[i] = dist( gg, vv->label, ws[i]->label, wo, INFINITY, TRUE );
        if( cvw[i] ) {
            cvw[i]->fromv = vv;
            cvw[i]->tov = ws[i]->mirror;
        }
        
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
                        Path* yld = pathCombine( cuv[i], cvw[j] );
                        
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

void pqPush( Heap *pq, Vertex* item, long priority ) {
    heapInsert( pq, (void*)item, priority );
    //fibheap_insert( pq, priority, (void*)item );
}

Vertex* pqPop( Heap *pq, long* priority ) {
    //*priority = fibheap_min_key( pq );
    //return (Vertex*)fibheap_extract_min( pq );
    return (Vertex*)heapPop( pq, priority );
    
}

int get_importance(int degree_in, int degree_out, int n_shortcuts, int deleted_neighbors) {
    
    int edge_difference = n_shortcuts - (degree_in+degree_out);
    
    return edge_difference + deleted_neighbors;
}

Heap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit ) {
    //fibheap* pq = fibheap_new();
    Heap* pq = heapNew( 100 );

    long n;
    int i;
    Vertex** vertices = gVertices( gg, &n );
    for(i=0; i<n; i++) {
        Vertex* vv = vertices[i];
        int n_shortcuts;
        Path** shortcuts = get_shortcuts( gg, vv, wo, search_limit, &n_shortcuts );
        int imp = get_importance( vv->degree_in, vv->degree_out, n_shortcuts, vv->deleted_neighbors );
        printf( "%s %d/%ld, prio:%d\n", vv->label, i+1, n, imp );
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


CH* get_contraction_hierarchies(Graph* gg, WalkOptions* wo, int search_limit) {
    Heap* pq = init_priority_queue( gg, wo, search_limit );

    Graph* gup = gNew();
    Graph* gdown = gNew();
    CH* ret = chNew( gup, gdown );
    
    Vertex* vertex;
    long n = gSize( gg );
    
    int i = 0;
    while( !heapEmpty(pq) ) {
        i++;
        
        long prio;
        vertex = pqPop( pq, &prio );
        
        //printf( "new vertex candidate %s\n", vertex->label );
        
        // make sure priority of current vertex
        Path** shortcuts;
        int n_shortcuts;
        while(1) {
            shortcuts = get_shortcuts( gg, vertex, wo, search_limit, &n_shortcuts );
            long new_prio = get_importance( vertex->degree_in, vertex->degree_out, n_shortcuts, vertex->deleted_neighbors );
            if(new_prio == prio) {
                break;
            } else {
                printf( "updated priority %ld != old priority %ld, reevaluate\n", new_prio, prio );
                
                //the shortcuts are invalid; delete them
                int k;
                for(k=0; k<n_shortcuts; k++) {
                    pathDestroy( shortcuts[k] );
                }
                free( shortcuts );
                
                pqPush( pq, vertex, new_prio );
                vertex = pqPop( pq, &prio );
                //printf( "new vertex candidate %s\n", vertex->label );
            }
        }
        
        printf( "%s has %d deleted neighbors\n", vertex->label, vertex->deleted_neighbors ); 
        printf( "contract %d/%ld %s (prio:%ld) with %d shortcuts\n", i, n, vertex->label, prio, n_shortcuts );
            
        // ADD SHORTCUTS
        int j;
        for(j=0; j<n_shortcuts; j++) {
            // ADD SHORTCUT
            Combination* shortcut_payload = pathToEdgePayload( shortcuts[j] );
            
            //State* s0 = epWalk( (EdgePayload*)shortcut_payload, stateNew(0,0), woNew() ); //TEMP
            //printf( "add %s %s %p (%ld long)\n", shortcuts[j]->fromv->label, shortcuts[j]->tov->label, shortcut_payload, s0->weight );
            
            gAddEdge( gg, shortcuts[j]->fromv->label, shortcuts[j]->tov->label, (EdgePayload*)shortcut_payload );
        }
        
        int k;
        for(k=0; k<n_shortcuts; k++) {
            pathDestroy( shortcuts[k] );
        }
        free( shortcuts );

        // move edges from gg to gup and gdown
        // vertices that are still in the graph are, by definition, of higher importance than the one
        // currently being plucked from the graph. Edges that go out are upward edges. Edges that are coming in
        // are downward edges.

        // incoming, therefore downward
        gAddVertex( gdown, vertex->label );
        ListNode* incoming = vGetIncomingEdgeList( vertex );
        while(incoming) {
            Edge* ee = incoming->data;
            gAddVertex( gdown, ee->from->label );
            gAddEdge( gdown, ee->from->label, ee->to->label, ee->payload );
            incoming = incoming->next;
        }
            
        // outgoing, therefore upward
        gAddVertex( gup, vertex->label );
        ListNode* outgoing = vGetOutgoingEdgeList( vertex );
        while(outgoing) {
            Edge* ee = outgoing->data;
            
            ee->to->deleted_neighbors++;
            
            gAddVertex( gup, ee->to->label );
            gAddEdge( gup, ee->from->label, ee->to->label, ee->payload );
            outgoing = outgoing->next;
        }
            
        // TODO inform neighbors their neighbor is being deleted
        
        
        gRemoveVertex( gg, vertex->label, FALSE );
    }
    
    heapDestroy( pq );
    
    return ret;
}
