
#include "../graphserver.h"

//WAIT FUNCTIONS
Wait*
waitNew(long end, Timezone* timezone) {
    Wait* ret = (Wait*)malloc(sizeof(Wait));
    ret->external_id = 0;
    ret->type = PL_WAIT;
    ret->end = end;
    ret->timezone = timezone;
    
    ret->walk = waitWalk;
    ret->walkBack = waitWalkBack;
    
    return ret;
}

void
waitDestroy(Wait* tokill) {
    free(tokill);
}

long
waitGetEnd(Wait* this) {
    return this->end;
}

Timezone*
waitGetTimezone(Wait* this) {
    return this->timezone;
}


inline State*
waitWalk(EdgePayload* superthis, State* state, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( state );
    
    ret->prev_edge = superthis;
    
    long secs_since_local_midnight = (state->time+tzUtcOffset(this->timezone, state->time))%SECS_IN_DAY;
    long wait_time = this->end - secs_since_local_midnight;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time += wait_time;
    ret->weight += wait_time;
    
    return ret;
}

inline State*
waitWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( state );
    
    ret->prev_edge = superthis;
    
    long secs_since_local_midnight = (state->time+tzUtcOffset(this->timezone, state->time))%SECS_IN_DAY;
    long wait_time = secs_since_local_midnight - this->end;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time -= wait_time;
    ret->weight += wait_time;
    
    return ret;
}
