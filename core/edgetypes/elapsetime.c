#include "../graphserver.h"

//ElapseTime FUNCTIONS
ElapseTime*
elapseTimeNew(long seconds) {
    ElapseTime* ret = (ElapseTime*)malloc(sizeof(ElapseTime));
    ret->external_id = 0;
    ret->type = PL_ELAPSE_TIME;
    ret->seconds = seconds;
    
    ret->walk = elapseTimeWalk;
    ret->walkBack = elapseTimeWalkBack;
    
    return ret;
}

void
elapseTimeDestroy(ElapseTime* tokill) {
    free(tokill);
}

long
elapseTimeGetSeconds(ElapseTime* this) {
    return this->seconds;
}

inline State*
elapseTimeWalkGeneral(EdgePayload* this, State* state, WalkOptions* options, int forward) {
  
  State* ret = stateDup( state );
  
  int delta_t = ((ElapseTime*)this)->seconds;
  
  if( forward ) {
    elapse_time_and_service_period_forward(ret, state, delta_t);
  } else {
    elapse_time_and_service_period_backward(ret, state, delta_t);
  }

  // this could have a multiplier via WalkOptions, but this is currently not necessary
  ret->weight += delta_t;
  ret->prev_edge = this;

  return ret;
}

inline State*
elapseTimeWalk(EdgePayload* this, State* state, WalkOptions* options) {
    return elapseTimeWalkGeneral( this, state, options, TRUE );
}

inline State*
elapseTimeWalkBack(EdgePayload* this, State* state, WalkOptions* options) {
    return elapseTimeWalkGeneral( this, state, options, FALSE );
}
