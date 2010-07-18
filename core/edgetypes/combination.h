
#ifndef _COMBINATION_H_
#define _COMBINATION_H_

//---------------DECLARATIONS FOR COMBINATION CLASS---------------------

struct Combination {
  edgepayload_t type;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  EdgePayload* first;
  EdgePayload* second;
} ;

Combination*
comboNew(EdgePayload* first, EdgePayload* second);

void
comboDestroy(Combination* tokill);

inline State*
comboWalk(EdgePayload* this, State* param, WalkOptions* options);

inline State*
comboWalkBack(EdgePayload* this, State* param, WalkOptions* options);

EdgePayload*
comboGetFirst(Combination* this);

EdgePayload*
comboGetSecond(Combination* this);

#endif
