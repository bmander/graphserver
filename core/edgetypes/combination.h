
#ifndef _COMBINATION_H_
#define _COMBINATION_H_

//---------------DECLARATIONS FOR COMBINATION CLASS---------------------

struct Combination {
  edgepayload_t type;
  long external_id;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  int cap;
  int n;
  EdgePayload** payloads;

  long cache_deltaw_forward;
  long cache_deltat_forward;
  State *cache_state_forward;
  long cache_deltaw_reverse;
  long cache_deltat_reverse;
  State *cache_state_reverse;
    
} ;

Combination*
comboNew(int cap) ;

void
comboAdd(Combination *this, EdgePayload *ep) ;

void
comboDestroy(Combination* this) ;

inline State*
comboWalk(EdgePayload* superthis, State* param, WalkOptions* options) ;

inline State*
comboWalkBack(EdgePayload* superthis, State* param, WalkOptions* options) ;

EdgePayload*
comboGet(Combination *this, int i) ;

int
comboN(Combination *this) ;

#endif
