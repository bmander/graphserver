#ifndef _EDGEPAYLOAD_H_
#define _EDGEPAYLOAD_H_

//---------------DECLARATIONS FOR EDGEPAYLOAD CLASS---------------------

struct EdgePayload {
  edgepayload_t type;
  long external_id;
  State* (*walk)(struct EdgePayload*, struct State*, struct WalkOptions*);
  State* (*walkBack)(struct EdgePayload*, struct State*, struct WalkOptions*);
} ;

EdgePayload*
epNew( edgepayload_t type, void* payload );

void
epDestroy( EdgePayload* this );

edgepayload_t
epGetType( EdgePayload* this );

long
epGetExternalId( EdgePayload* this );

void
epSetExternalId( EdgePayload *this, long external_id );

State*
epWalk( EdgePayload* this, State* param, WalkOptions* options );

State*
epWalkBack( EdgePayload* this, State* param, WalkOptions* options );

#endif
