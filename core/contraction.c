#include "graphserver.h"
#include "graph.h"
#include "heap.h"
#include "contraction.h"
#include <stdio.h>
#define TRUE 1
#define FALSE 0

CH* chNew() {
    CH* ret = (CH*)malloc(sizeof(CH));
    ret->up = gNew();
    ret->down = gNew();
    return ret;
}

Graph* chUpGraph( CH* this ) {
    return this->up;
}

Graph* chDownGraph( CH* this ) {
    return this->down;
}

void chDestroy( CH* this ) {
    gDestroyBasic( this->up, 0 );
    gDestroyBasic( this->down, 0 );
    free( this );
}

CHPath* chpNew( int n, long length ) {
  CHPath *this = (CHPath*)malloc(sizeof(CHPath));
  this->n = n;
  this->payloads = (EdgePayload**)malloc(n*sizeof(EdgePayload*));
  this->length = length;

  return this;
}

CHPath* chpNewHollow( long length ) {
    CHPath *this = (CHPath*)malloc(sizeof(CHPath));
    this->n = 0;
    this->payloads = NULL;
    this->fromv = NULL;
    this->tov = NULL;
    this->length = length;
    
    return this;
}

int chpLength( CHPath* this ) {
    if(!this) {
        return INFINITY;
    }
    
    return this->length;
}

CHPath* chpCombine( CHPath* a, CHPath* b ) {
    CHPath* ret = chpNew( a->n+b->n, a->length+b->length );
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

void chpDestroy( CHPath* this ) {
    if(!this) return;
    
    free( this->payloads );
    free( this );
}

Combination* pathToEdgePayload( CHPath* this ) {
    Combination* ret = comboNew( this->n );
    int i;
    for(i=0; i<this->n; i++) {
        comboAdd( ret, this->payloads[i] );
    }
    return ret;
}
    
CHPath* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo, int weightlimit, int return_full_path )  {
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
    
    CHPath* ret;
    
    if( return_full_path ) {
        // get path length
        int pathlength = 0;
        Edge *currparent = sptvGetParent( curs );
        while(currparent) {
            pathlength++;
            currparent = sptvGetParent( (SPTVertex*)currparent->from );
        }
        
        ret = chpNew( pathlength, curs->state->weight );
        int i;
        for(i=pathlength-1; i>=0; i--) {
            Edge* parent = sptvGetParent( curs ) ;
            ret->payloads[i] = parent->payload;
            curs = (SPTVertex*)parent->from;
        }
    } else {
        ret = chpNewHollow( curs->state->weight );
    }
    
    sptDestroy( spt );
    
    return ret;
}

SPTVertex** gNearbyBehind( Graph *gg, Vertex *vv, int search_limit, long *n ) {
    State* dummy = stateNew( 1, 0 );
    WalkOptions *wo = woNew();
    ShortestPathTree *sptout = gShortestPathTree( gg, vv->label, "bogus", dummy, wo, INFINITY, search_limit, INFINITY );
    SPTVertex** ret = sptVertices( sptout, n );
    
    woDestroy( wo );
    sptDestroy( sptout );
    
    return ret;
}

CHPath** get_shortcuts( Graph *gg, Vertex* vv, WalkOptions* wo, int search_limit, int* n ) {
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
    CHPath** ret = (CHPath**)malloc(n_us*n_ws*sizeof(CHPath*));
    int count = 0;
    
    // GET PATHS c(u,v) FROM ALL us TO v
    CHPath** cuv = (CHPath**)malloc(n_us*sizeof(CHPath*));
    for(i=0; i<n_us; i++) {
        cuv[i] = dist( gg, us[i]->label, vv->label, wo, INFINITY, TRUE );
        if(cuv[i]) {
          cuv[i]->fromv = us[i]->mirror;
          cuv[i]->tov = vv;
        }
    }
    
    // GET PATHS c(v,w) FROM v to ALL ws, FINDING THE MAX c(v,w)
    CHPath** cvw = (CHPath**)malloc(n_ws*sizeof(CHPath*));
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
        
            int cuv_length = chpLength( cuv[i] );
            int weightlimit = cuv_length+max_cvw;
            
            //FOR EACH W
            for(j=0; j<n_ws; j++) {
                SPTVertex* w = ws[j];
                
                // the path c(v,w) must be non-NULL, and u!=w
                if( cvw[j] && strcmp(u->label,w->label)!=0 ) {
                    CHPath* duw = dist( gg, u->label, w->label, wo, weightlimit, FALSE);
                    
                    // IF THE PATH AROUND IS LONGER THAN THE PATH THROUGH, ADD THE PATH THROUGH TO THE SHORTCUTS
                    if( cuv_length+chpLength(cvw[j]) < chpLength(duw) ) {
                        CHPath* yld = chpCombine( cuv[i], cvw[j] );
                        ret[count] = yld;
                        count++;
                    }
                    
                    chpDestroy( duw );
                }
            }
        }
    }
    gSetVertexEnabled( gg, vv->label, 1 );
    
    for(i=0; i<n_us; i++) {
        chpDestroy( cuv[i] );
    }
    free( cuv );
    for(i=0; i<n_ws; i++) {
        chpDestroy( cvw[i] );
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
}

Vertex* pqPop( Heap *pq, long* priority ) {
    return (Vertex*)heapPop( pq, priority );
}

int get_importance(Vertex *vertex, int n_shortcuts) {
    
    int edge_difference = n_shortcuts - (vertex->degree_in+vertex->degree_out);
    
    return edge_difference + vertex->deleted_neighbors;
}

Heap* init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit ) {
    Heap* pq = heapNew( 100 );

    long n;
    int i;
    Vertex** vertices = gVertices( gg, &n );
    for(i=0; i<n; i++) {
        Vertex* vv = vertices[i];
        int n_shortcuts=0;
        CHPath** shortcuts = get_shortcuts( gg, vv, wo, search_limit, &n_shortcuts );
        int imp = get_importance( vv, n_shortcuts );
        printf( "%s %d/%ld, prio:%d\n", vv->label, i+1, n, imp );
        pqPush( pq, vv, imp );
        int j;
        for(j=0; j<n_shortcuts; j++){
            chpDestroy( shortcuts[j] );
        }
        free( shortcuts );
    }
    free(vertices);
    return pq;
}


CH* get_contraction_hierarchies(Graph* gg, WalkOptions* wo, int search_limit) {
    Heap* pq = init_priority_queue( gg, wo, search_limit );

    CH* ret = chNew( );
    
    Vertex* vertex;
    long n = gSize( gg );
    
    int i = 0;
    while( !heapEmpty(pq) ) {
        i++;
        
        long prio;
        vertex = pqPop( pq, &prio );
        
        // make sure priority of current vertex
        CHPath** shortcuts;
        int n_shortcuts;
        while(1) {
            shortcuts = get_shortcuts( gg, vertex, wo, search_limit, &n_shortcuts );
            long new_prio = get_importance( vertex, n_shortcuts );
            if(new_prio == prio) {
                break;
            } else {
                printf( "updated priority %ld != old priority %ld, reevaluate\n", new_prio, prio );
                
                //the shortcuts are invalid; delete them
                int k;
                for(k=0; k<n_shortcuts; k++) {
                    chpDestroy( shortcuts[k] );
                }
                free( shortcuts );
                
                pqPush( pq, vertex, new_prio );
                vertex = pqPop( pq, &prio );
            }
        }
        
        printf( "%s has %d deleted neighbors\n", vertex->label, vertex->deleted_neighbors ); 
        printf( "contract %d/%ld %s (prio:%ld) with %d shortcuts\n", i, n, vertex->label, prio, n_shortcuts );
            
        // ADD SHORTCUTS
        int j;
        for(j=0; j<n_shortcuts; j++) {
            // ADD SHORTCUT
            Combination* shortcut_payload = pathToEdgePayload( shortcuts[j] );
            
            gAddEdge( gg, shortcuts[j]->fromv->label, shortcuts[j]->tov->label, (EdgePayload*)shortcut_payload );
        }
        
        int k;
        for(k=0; k<n_shortcuts; k++) {
            chpDestroy( shortcuts[k] );
        }
        free( shortcuts );

        // move edges from gg to gup and gdown
        // vertices that are still in the graph are, by definition, of higher importance than the one
        // currently being plucked from the graph. Edges that go out are upward edges. Edges that are coming in
        // are downward edges.

        // incoming, therefore downward
        gAddVertex( ret->down, vertex->label );
        ListNode* incoming = vGetIncomingEdgeList( vertex );
        while(incoming) {
            Edge* ee = incoming->data;
            gAddVertex( ret->down, ee->from->label );
            gAddEdge( ret->down, ee->from->label, ee->to->label, ee->payload );
            incoming = incoming->next;
        }
            
        // outgoing, therefore upward
        gAddVertex( ret->up, vertex->label );
        ListNode* outgoing = vGetOutgoingEdgeList( vertex );
        while(outgoing) {
            Edge* ee = outgoing->data;
            
            ee->to->deleted_neighbors++;
            
            gAddVertex( ret->up, ee->to->label );
            gAddEdge( ret->up, ee->from->label, ee->to->label, ee->payload );
            outgoing = outgoing->next;
        }
        
        gRemoveVertex( gg, vertex->label, FALSE );
    }
    
    heapDestroy( pq );
    
    return ret;
}
