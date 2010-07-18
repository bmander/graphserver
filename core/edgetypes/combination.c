#include "../graphserver.h"

//=========COMBINATION FUNCTIONS==============

Combination*
comboNew(int cap) {
    Combination* ret = (Combination*)malloc(sizeof(Combination));
    ret->type = PL_COMBINATION;
    ret->cap = cap;
    ret->n = 0;
    ret->payloads = (EdgePayload**)malloc(cap*sizeof(EdgePayload*));
    
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
    free( this->payloads );
    free( this );
}

inline State*
comboWalk(EdgePayload* superthis, State* param, WalkOptions* options) {
    Combination* this = (Combination*)superthis;
    
    if( this->n == 0 ) return NULL;
        
    State* ret = epWalk( this->payloads[0], param, options );
    
    int i;
    for(i=1; i<this->n; i++) {
        State* intermediate = ret;
        ret = epWalk( this->payloads[i], intermediate, options );
        stateDestroy( intermediate );
    }
    
    return ret;
}

inline State*
comboWalkBack(EdgePayload* superthis, State* param, WalkOptions* options) {
    Combination* this = (Combination*)superthis;
    
    if( this->n == 0 ) return NULL;
        
    State* ret = epWalkBack( this->payloads[this->n-1], param, options );
    
    int i;
    for(i=this->n-2; i>=0; i--) {
        State* intermediate = ret;
        ret = epWalkBack( this->payloads[i], intermediate, options );
        stateDestroy( intermediate );
    }
    
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

