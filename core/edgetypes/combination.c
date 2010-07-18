#include "../graphserver.h"

//=========COMBINATION FUNCTIONS==============

Combination*
comboNew(EdgePayload* first, EdgePayload* second) {
    Combination* ret = (Combination*)malloc(sizeof(Combination));
    ret->type = PL_COMBINATION;
    ret->first = first;
    ret->second = second;

    ret->walk = &comboWalk;
    ret->walkBack = &comboWalkBack;

    return ret;
}

void
comboDestroy(Combination* tokill) {
    free( tokill );
}

inline State*
comboWalk(EdgePayload* this, State* param, WalkOptions* options) {
    State* intermediate = epWalk( ((Combination*)this)->first, param, options );
    State* ret = epWalk( ((Combination*)this)->second, intermediate, options );
    stateDestroy( intermediate );
    return ret;
}

inline State*
comboWalkBack(EdgePayload* this, State* param, WalkOptions* options) {
    State* intermediate = epWalkBack( ((Combination*)this)->second, param, options );
    State* ret = epWalkBack( ((Combination*)this)->first, intermediate, options );
    stateDestroy( intermediate );
    return ret;
}

EdgePayload*
comboGetFirst(Combination* this) {
    return this->first;
}

EdgePayload*
comboGetSecond(Combination* this) {
    return this->second;
}

