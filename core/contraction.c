#include "graphserver.h"
#include "graph.h"
#include "contraction.h"
#include <stdio.h>

CHPath* chpNew( int n, long length ) {
  CHPath *this = (CHPath*)malloc(sizeof(CHPath));
  this->n = n;
  this->payloads = (EdgePayload**)malloc(n*sizeof(EdgePayload*));
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
    
CHPath* dist( Graph *gg, char* from_v_label, char* to_v_label, WalkOptions *wo )  {
    if( strcmp( from_v_label, to_v_label ) == 0 ) {
        return NULL;
    }
    
    State *dummy = stateNew(0,0);
    ShortestPathTree* spt = gShortestPathTree( gg, from_v_label, to_v_label, dummy, wo, INFINITY, INFINITY, INFINITY );
    
    SPTVertex* curs = sptGetVertex( spt, to_v_label );
    
    if(!curs) {
        sptDestroy( spt );
        return NULL;
    }
    
    CHPath *ret = chpNew( curs->hop+1, curs->state->weight );
    int i;
    for(i=curs->hop; i>0; i--) {
        Edge* parent = sptvGetParent( curs ) ;
        ret->payloads[i] = parent->payload;
        curs = (SPTVertex*)parent->from;
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
    ShortestPathTree* sptin = gShortestPathTreeRetro( gg, "bogus", vv->label, dummy, wo, INFINITY, search_limit, INFINITY );
    SPTVertex** us = sptVertices( sptin, &n_us );
    State *dummy2 = stateNew( 0, 0 );
    ShortestPathTree* sptout = gShortestPathTree( gg, vv->label, "bogus", dummy2, wo, INFINITY, search_limit, INFINITY );
    SPTVertex** ws = sptVertices( sptout, &n_ws );

    // THE RETURN ARRAY CANNOT BE LARGER THAN len(u)*len(w) PATHS
    CHPath** ret = (CHPath**)malloc(n_us*n_ws*sizeof(CHPath*));
    int count = 0;
    
    // GET PATHS FROM ALL us TO v
    CHPath** cuv = (CHPath**)malloc(n_us*sizeof(CHPath*));
    for(i=0; i<n_us; i++) {
        cuv[i] = dist( gg, us[i]->label, vv->label, wo );
        printf( "uv path from %s to %s is %d\n", us[i]->label,vv->label, chpLength( cuv[i] ) );
    }
    
    // GET PATHS FROM v to ALL ws
    CHPath** cvw = (CHPath**)malloc(n_ws*sizeof(CHPath*));
    for(i=0; i<n_ws; i++) {
        cvw[i] = dist( gg, vv->label, ws[i]->label, wo );
        printf( "vw path from %s to %s is %d\n", vv->label, ws[i]->label, chpLength( cvw[i] ) );
    }
    
    // FOR ALL us AND ws, SEE IF THERE IS A PATH FROM u TO w IGNORING v THAT IS SHORTER THAN THE PATH THROUGH v
    gSetVertexEnabled( gg, vv->label, 0 );
    for(i=0; i<n_us; i++) {
        SPTVertex* u = us[i];
        int cuv_length = chpLength( cuv[i] );
        for(j=0; j<n_ws; j++) {
            SPTVertex* w = ws[j];
            if( u != w ) {
                CHPath* duw = dist( gg, u->label, w->label, wo);
                
                printf( "duw.length: %d\n", chpLength( duw ) );
                printf( "shortcut length: %d\n", cuv_length+chpLength(cvw[j]) );
                
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
