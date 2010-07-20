
#include "../graphserver.h"

//EGRESS FUNCTIONS
Egress*
egressNew(const char *name, double length) {
  Egress* ret = (Egress*)malloc(sizeof(Egress));
  ret->external_id = 0;
  ret->type = PL_EGRESS;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
  
  //bind functions to methods
  ret->walk = &egressWalk;
  ret->walkBack = &egressWalkBack;

  return ret;
}

void
egressDestroy(Egress* tokill) {
  free(tokill->name);
  free(tokill);
}

char*
egressGetName(Egress* this) {
    return this->name;
}

double
egressGetLength(Egress* this) {
    return this->length;
}


inline State*
egressWalkGeneral(EdgePayload* superthis, State* state, WalkOptions* options, int forward) {
  Egress* this = (Egress*)superthis;
  State* ret = stateDup( state );

  double end_dist = state->dist_walked + this->length;
  // no matter what the options say (e.g. you're on a bike), 
  // the walking speed should be 1.1 mps, because you can't ride in
  // a station
  long delta_t = (long)(this->length/1.1);
  long delta_w = delta_t*options->walking_reluctance;
  if(end_dist > options->max_walk)
    delta_w += (end_dist - options->max_walk)*options->walking_overage*delta_t;

  if( forward ) {
    elapse_time_and_service_period_forward(ret, state, delta_t);
  } else {
    elapse_time_and_service_period_backward(ret, state, delta_t);
  }

  ret->weight        += delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge = superthis;

  return ret;
}

inline State*
egressWalk(EdgePayload* superthis, State* state, WalkOptions* options) {
    return egressWalkGeneral( superthis, state, options, TRUE );
}

inline State*
egressWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
    return egressWalkGeneral( superthis, state, options, FALSE );
}
