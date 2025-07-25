#ifndef EDGEPAYLOAD_H
#define EDGEPAYLOAD_H

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
epGetType( const EdgePayload* this );

long
epGetExternalId( const EdgePayload* this );

void
epSetExternalId( EdgePayload *this, long external_id );

State*
epWalk( const EdgePayload* this, State* param, WalkOptions* options );

State*
epWalkBack( const EdgePayload* this, State* param, WalkOptions* options );

#endif
