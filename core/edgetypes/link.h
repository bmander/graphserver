typedef struct Link {
  edgepayload_t type;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  char* name;
} Link;

Link*
linkNew();

void
linkDestroy(Link* tokill);

inline State*
linkWalk(EdgePayload* this, State* param, WalkOptions* options);

inline State*
linkWalkBack(EdgePayload* this, State* param, WalkOptions* options);

char*
linkGetName(Link* this);