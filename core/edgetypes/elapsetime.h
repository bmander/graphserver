//---------------DECLARATIONS FOR ELAPSE TIME CLASS------------------------

typedef struct ElapseTime {
    edgepayload_t type;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    long seconds;
} ElapseTime;

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