#ifndef _LINK_H_
#define _LINK_H_

//---------------DECLARATIONS FOR LINK  CLASS---------------------

struct Link {
  edgepayload_t type;
  long external_id;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
    
  char* name;
};

Link*
linkNew(void);

void
linkDestroy(Link* tokill);

inline State*
linkWalk(EdgePayload* this, State* param, WalkOptions* options);

inline State*
linkWalkBack(EdgePayload* this, State* param, WalkOptions* options);

char*
linkGetName(Link* this);

#endif
