
#include "../graphserver.h"

//LINK FUNCTIONS
Link*
linkNew() {
  Link* ret = (Link*)malloc(sizeof(Link));
  ret->external_id = 0;
  ret->type = PL_LINK;
    
  //bind functions to methods
  ret->walk = &linkWalk;
  ret->walkBack = &linkWalkBack;

  return ret;
}

void
linkDestroy(Link* tokill) {
  free( tokill );
}

inline State*
linkWalkBackGeneral(EdgePayload* this, State* state, WalkOptions* options) {
    
  State* ret = stateDup( state );

  ret->prev_edge = this;

  return ret;
}

inline State*
linkWalkBack(EdgePayload* this, State* state, WalkOptions* options) {
  return linkWalkBackGeneral(this, state, options);
}

inline State*
linkWalk(EdgePayload* this, State* state, WalkOptions* options) {
  return linkWalkBackGeneral(this, state, options);
}
