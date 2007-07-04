#include "edgetypes.h"
#include "math.h"
#include <stdio.h>

//STATE FUNCTIONS
State*
stateNew(long time) {
  State* ret = (State*)malloc( sizeof(State) );
  ret->time = time;
  ret->weight = 0;
  ret->dist_walked = 0;
  ret->num_transfers = 0;
  ret->prev_edge_name = NULL;
  ret->prev_edge_type = PL_NONE;
  ret->calendar_day = NULL;

  return ret;
}

State*
stateDup( State* this ) {
  State* ret = (State*)malloc( sizeof(State) );
  memcpy( ret, this, sizeof( State ) );
  return ret;
}

//the State object does not own State#calendar
void
stateDestroy(State* this) {
  free( this );
}

//--------------------EDGEPAYLOAD FUNCTIONS-------------------

EdgePayload*
epNew( edgepayload_t type, void* payload ) {
  EdgePayload* ret = (EdgePayload*)malloc(sizeof(EdgePayload));
  ret->type = type;
  ret->payload = payload;
  
  return ret;
}

EdgePayload*
epDup( EdgePayload* this ) {
  EdgePayload* ret = (EdgePayload*)malloc( sizeof(EdgePayload) );
  memcpy( ret, this, sizeof( EdgePayload ) );
  return ret;
}

void
epDestroy( EdgePayload* this, int destroy_payload ) {
  if( destroy_payload ) {
    switch( this->type ) {
      case PL_STREET:
        streetDestroy( this->payload );
        break;
      case PL_TRIPHOPSCHED:
        thsDestroy( this->payload );
        break;
      case PL_TRIPHOP:
        triphopDestroy( this->payload );
      case PL_LINK:
        linkDestroy( this->payload );
        break;
      default:
        free( this->payload );
    }
  }
  free( this );
}

State*
epWalk( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_STREET:
      return streetWalk( (Street*)this->payload, params );
    case PL_TRIPHOPSCHED:
      return thsWalk((TripHopSchedule*)this->payload, params);
    case PL_TRIPHOP:
      return triphopWalk((TripHop*)this->payload, params );
    case PL_LINK:
      return linkWalk((Link*)this->payload, params);
    default:
      return NULL;
  }
}

State*
epWalkBack( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_STREET:
      return streetWalkBack( (Street*)this->payload, params );
    case PL_TRIPHOPSCHED:
      return thsWalkBack((TripHopSchedule*)this->payload, params);
    case PL_TRIPHOP:
      return triphopWalkBack((TripHop*)this->payload, params);
    case PL_LINK:
      return linkWalkBack((Link*)this->payload, params);
    default:
      return NULL;
  }
}

EdgePayload*
epCollapse( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_TRIPHOPSCHED:
      return epNew( PL_TRIPHOP, thsCollapse( (TripHopSchedule*)this->payload, params) );
    default:
      return epDup( this );
  }
}

EdgePayload*
epCollapseBack( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_TRIPHOPSCHED:
      return epNew( PL_TRIPHOP, thsCollapseBack( (TripHopSchedule*)this->payload, params) );
    default:
      return epDup( this );
  }
}

//EdgePayload*
//epCollapse( EdgePayload* this, State* param );

//EdgePayload*
//epCollapseBack( EdgePayload* this, State* param );

//LINK FUNCTIONS
Link*
linkNew() {
  Link* ret = (Link*)malloc(sizeof(Link));
  ret->name = (char*)malloc(5*sizeof(char));
  strcpy(ret->name, "LINK");

  return ret;
}

void
linkDestroy(Link* tokill) {
  free( tokill->name );
  free( tokill );
}

//STREET FUNCTIONS
Street*
streetNew(const char *name, double length) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;

  return ret;
}

void
streetDestroy(Street* tokill) {
  free(tokill->name);
  free(tokill);
}

//TRIPHOP FUNCTIONS

//tests the order of the hops, by terminus time, for use with sorting functions
int hopcmp(const void* a, const void* b) {
  TripHop* aa = (TripHop*)a;
  TripHop* bb = (TripHop*)b;
  if(aa->arrive < bb->arrive)
    return -1;
  else if(aa->arrive > bb->arrive)
    return 1;
  else {
    return 0;
  }
}

/*
 * Receives n tuples consisting if [depart, arrive, trip_id], all associated with one service_id
 */

TripHopSchedule*
thsNew( int *departs, int *arrives, char **trip_ids, int n, ServiceId service_id, CalendarDay* calendar, int timezone_offset ) {
  TripHopSchedule* ret = (TripHopSchedule*)malloc(sizeof(TripHopSchedule));
  ret->hops = (TripHop*)malloc(n*sizeof(TripHop));
  ret->n = n;
  ret->service_id = service_id;
  ret->calendar = calendar;
  ret->timezone_offset = timezone_offset;

  int i;
  for(i=0; i<n; i++) {
    ret->hops[i].depart = departs[i];
    ret->hops[i].arrive = arrives[i];
    ret->hops[i].transit = arrives[i] - departs[i];
    ret->hops[i].trip_id = trip_ids[i];
    ret->hops[i].schedule = ret;
  }

  //make sure departure and arrival arrays are sorted, as they're subjected to a binsearch
  qsort(ret->hops, n, sizeof(TripHop), hopcmp);

  return ret; // return NULL;
}

inline long
thsSecondsSinceMidnight( TripHopSchedule* this, State* param ) {
    //difference between utc midnight and local midnight
    long utc_offset = this->timezone_offset + param->calendar_day->daylight_savings;
    //difference between local midnight and calendar day begin
    long since_midnight_local = (param->calendar_day->begin_time+utc_offset)%SECONDS_IN_DAY;
    //seconds since the calendar day began
    long since_calday_begin = param->time - param->calendar_day->begin_time;
    //seconds since local midnight
    return since_midnight_local + since_calday_begin;
}

//DEBUG CODE
void
thsPrintHops(TripHopSchedule* this) {
  int i;
  printf("--==--\n");
  for(i=0; i<this->n; i++) {
    printf("Hop: %d, %d, %s\n", this->hops[i].depart, this->hops[i].arrive, this->hops[i].trip_id);
  }
  printf("--==--\n");
}

void
thsDestroy(TripHopSchedule* this) {
  int i;

  free(this->hops);
  free(this);
}

#undef ROUTE_REVERSE
#include "edgeweights.c"
#define ROUTE_REVERSE
#include "edgeweights.c"
#undef ROUTE_REVERSE
