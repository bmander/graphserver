
#ifndef _COMBINATION_H_
#define _COMBINATION_H_

//---------------DECLARATIONS FOR COMBINATION CLASS---------------------

struct Combination {
  edgepayload_t type;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  int cap;
  int n;
  EdgePayload** payloads;
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
