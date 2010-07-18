#include "graphserver.h"
#include "graph.h"
#include "fibheap/fibheap.h"
#include "contraction.h"
#include <stdio.h>
#define TRUE 1
#define FALSE 0

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
    }
    
    // GET PATHS c(v,w) FROM v to ALL ws, FINDING THE MAX c(v,w)
    CHPath** cvw = (CHPath**)malloc(n_ws*sizeof(CHPath*));
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
                        CHPath* yld = chpCombine( cuv[i], cvw[i] );
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

void pqPush( fibheap_t pq, Vertex* item, int priority ) {
    fibheap_insert( pq, priority, (void*)item );
}

Vertex* pqPop( fibheap_t pq, int* priority ) {
    *priority = fibheap_min_key( pq );
    return (Vertex*)fibheap_extract_min( pq );
}

int get_importance(int degree_in, int degree_out, int n_shortcuts) {
    int edge_difference = n_shortcuts - (degree_in+degree_out);
    return edge_difference;
}

fibheap_t init_priority_queue( Graph* gg, WalkOptions* wo, int search_limit ) {
    fibheap_t pq = fibheap_new();

    long n;
    int i;
    Vertex** vertices = gVertices( gg, &n );
    for(i=0; i<n; i++) {
        Vertex* vv = vertices[i];
        printf( "%s %d/%ld\n", vv->label, i+1, n );
        int n_shortcuts;
        CHPath** shortcuts = get_shortcuts( gg, vv, wo, search_limit, &n_shortcuts );
        int imp = get_importance( vv->degree_in, vv->degree_out, n_shortcuts );
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
