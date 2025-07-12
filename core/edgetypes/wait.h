
//---------------DECLARATIONS FOR WAIT CLASS------------------------

struct Wait {
    edgepayload_t type;
    long external_id;
    State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
    State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
    long end;
    Timezone* timezone;
} ;

Wait*
waitNew(long end, Timezone* timezone);

void
waitDestroy(Wait* tokill);

State*
waitWalk(EdgePayload* superthis, State* param, WalkOptions* options);

State*
waitWalkBack(EdgePayload* superthis, State* param, WalkOptions* options);

long
waitGetEnd(Wait* this);

Timezone*
waitGetTimezone(Wait* this);
