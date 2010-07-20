#ifndef _EGRESS_H_
#define _EGRESS_H_

//---------------DECLARATIONS FOR EGRESS CLASS---------------------

struct Egress {
   edgepayload_t type;
   long external_id;
   State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
   State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
   char* name;
   double length;
} ;

Egress*
egressNew(const char *name, double length);

void
egressDestroy(Egress* tokill);

inline State*
egressWalk(EdgePayload* superthis, State* state, WalkOptions* options);

inline State*
egressWalkBack(EdgePayload* superthis, State* state, WalkOptions* options);

char*
egressGetName(Egress* this);

double
egressGetLength(Egress* this);

#endif
