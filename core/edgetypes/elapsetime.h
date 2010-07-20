#ifndef _ELAPSETIME_H_
#define _ELAPSETIME_H_

//---------------DECLARATIONS FOR ELAPSE TIME CLASS------------------------

struct ElapseTime {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    long seconds;
} ;

ElapseTime*
elapseTimeNew(long seconds);

void
elapseTimeDestroy(ElapseTime* tokill);

inline State*
elapseTimeWalk(EdgePayload* superthis, State* param, WalkOptions* options);

inline State*
elapseTimeWalkBack(EdgePayload* superthis, State* param, WalkOptions* options);

long
elapseTimeGetSeconds(ElapseTime* this);

#endif
