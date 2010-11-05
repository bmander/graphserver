#include "graphserver.h"

//--------------------EDGEPAYLOAD FUNCTIONS-------------------

EdgePayload*
epNew( edgepayload_t type, void* payload ) {
  EdgePayload* ret = (EdgePayload*)malloc(sizeof(EdgePayload));
  ret->external_id = 0;
  ret->type = PL_NONE;
  return ret;
}

EdgePayload*
epDup( EdgePayload* this ) {
  EdgePayload* ret = (EdgePayload*)malloc( sizeof(EdgePayload) );
  memcpy( ret, this, sizeof( EdgePayload ) );
  return ret;
}

void
epDestroy( EdgePayload* this ) {
  switch( this->type ) {
    case PL_STREET:
      streetDestroy( (Street*)this );
      break;
    case PL_LINK:
      linkDestroy( (Link*)this );
      break;
    case PL_EXTERNVALUE:
      cpDestroy( (CustomPayload*)this );
      break;
    case PL_WAIT:
      waitDestroy( (Wait*)this );
      break;
    case PL_HEADWAY:
      headwayDestroy( (Headway*)this );
      break;
    case PL_EGRESS:
      egressDestroy( (Egress*)this ); 
      break;
    case PL_TRIPBOARD:
      tbDestroy( (TripBoard*)this );
      break;
    case PL_ALIGHT:
      alDestroy( (TripAlight*)this );
      break;
    case PL_CROSSING:
      crDestroy( (Crossing*)this );
      break;
    default:
      free( this );
  }
}

edgepayload_t
epGetType( EdgePayload* this ) {
    return this->type;
}

long
epGetExternalId( EdgePayload *this ) {
    return this->external_id;
}

void
epSetExternalId( EdgePayload *this, long external_id ) {
    this->external_id = external_id;
}

State*
epWalk( EdgePayload* this, State* state, WalkOptions* options ) {
  if( !this )
    return NULL;

  if( this->type == PL_EXTERNVALUE ) {
    return cpWalk( (CustomPayload*)this, state, options );
  }
  
  return this->walk( this, state, options );

}

State*
epWalkBack( EdgePayload* this, State* state, WalkOptions* options ) {
  if(!this)
    return NULL;

  if( this->type == PL_EXTERNVALUE ){
    return cpWalkBack( (CustomPayload*)this, state, options );
  }
  
  return this->walkBack( this, state, options );
}
