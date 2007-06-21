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

//the State object does not own it's contained calnedar
void
stateDestroy(State* this) {
  free( this );
}


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
thsNew( int *departs, int *arrives, char **trip_ids, int n, ServiceId service_id, CalendarDay* calendar, double timezone_offset ) {
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
  }

  //make sure departure and arrival arrays are sorted, as they're subjected to a binsearch
  qsort(ret->hops, n, sizeof(TripHop), hopcmp);

  return ret; // return NULL;
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
