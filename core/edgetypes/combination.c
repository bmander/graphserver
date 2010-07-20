#include "../graphserver.h"

//=========COMBINATION FUNCTIONS==============

Combination*
comboNew(int cap) {
    Combination* ret = (Combination*)malloc(sizeof(Combination));
    ret->external_id = 0;
    ret->type = PL_COMBINATION;
    ret->cap = cap;
    ret->n = 0;
    ret->payloads = (EdgePayload**)malloc(cap*sizeof(EdgePayload*));
    
    ret->cache_state_forward = NULL;
    ret->cache_state_reverse = NULL;
    
    ret->walk = &comboWalk;
    ret->walkBack = &comboWalkBack;
    
    return ret;
}

void
comboAdd(Combination *this, EdgePayload *ep) {
    if( this->n < this->cap ) {
      this->payloads[this->n] = ep;
      this->n++;
    }
}

void
comboDestroy(Combination* this) {
    if( this->cache_state_forward )
        stateDestroy( this->cache_state_forward );
    if( this->cache_state_reverse )
        stateDestroy( this->cache_state_reverse );
    
    free( this->payloads );
    free( this );
}

inline State*
comboWalk(EdgePayload* superthis, State* param, WalkOptions* options) {
    Combination* this = (Combination*)superthis;
    
    if( this->cache_state_forward ) {
        State* ret = stateDup( this->cache_state_forward );
        ret->weight = param->weight+this->cache_deltaw_forward;
        ret->time = param->time+this->cache_deltat_forward;
        return ret;
    }
    
    if( this->n == 0 ) return NULL;
        
    State* ret = epWalk( this->payloads[0], param, options );
    
    int i;
    for(i=1; i<this->n; i++) {
        State* intermediate = ret;
        ret = epWalk( this->payloads[i], intermediate, options );
        stateDestroy( intermediate );
    }
    
    this->cache_state_forward = stateDup( ret );
    this->cache_deltaw_forward = ret->weight - param->weight;
    this->cache_deltat_forward = ret->time - param->time;
    
    return ret;
}

inline State*
comboWalkBack(EdgePayload* superthis, State* param, WalkOptions* options) {
    Combination* this = (Combination*)superthis;
    
    if( this->cache_state_reverse ) {
        State* ret = stateDup( this->cache_state_reverse );
        ret->weight = param->weight+this->cache_deltaw_reverse;
        ret->time = param->time+this->cache_deltat_reverse;
        return ret;
    }
    
    if( this->n == 0 ) return NULL;
        
    State* ret = epWalkBack( this->payloads[this->n-1], param, options );
    
    int i;
    for(i=this->n-2; i>=0; i--) {
        State* intermediate = ret;
        ret = epWalkBack( this->payloads[i], intermediate, options );
        stateDestroy( intermediate );
    }
    
    this->cache_state_reverse = stateDup( ret );
    this->cache_deltaw_reverse = ret->weight - param->weight;
    this->cache_deltat_reverse = ret->time - param->time;
    
    return ret;
}

EdgePayload*
comboGet(Combination *this, int i) {
    if( i < this->n && i >= 0 ) {
        return this->payloads[i];
    } else {
        return NULL;
    }
}

int
comboN(Combination *this) {
    return this->n;
}

