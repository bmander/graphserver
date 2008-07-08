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

long
stateGetTime( State* this ) { return this->time; }

long
stateGetWeight( State* this) { return this->weight; }

double
stateGetDistWalked( State* this ) { return this->dist_walked; }

int
stateGetNumTransfers( State* this ) { return this->num_transfers; }

edgepayload_t
stateGetPrevEdgeType( State* this ) { return this->prev_edge_type; }

char*
stateGetPrevEdgeName( State* this ) { return this->prev_edge_name; }

CalendarDay*
stateCalendarDay( State* this ) { return this->calendar_day; }

void
stateSetTime( State* this, long time ) { this->time = time; }

void
stateSetWeight( State* this, long weight ) { this->weight = weight; }

void
stateSetDistWalked( State* this, double dist ) { this->dist_walked = dist; }

void
stateSetNumTransfers( State* this, int n) { this->num_transfers = n; }

void
stateSetCalendarDay( State* this,  CalendarDay* cal ) { this->calendar_day = cal; }

//--------------------EDGEPAYLOAD FUNCTIONS-------------------

EdgePayload*
epNew( edgepayload_t type, void* payload ) {
  EdgePayload* ret = (EdgePayload*)malloc(sizeof(EdgePayload));
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
    case PL_TRIPHOPSCHED:
      thsDestroy( (TripHopSchedule*)this );
      break;
    case PL_TRIPHOP:
      triphopDestroy( (TripHop*)this );
      break;
    case PL_LINK:
      linkDestroy( (Link*)this );
      break;
    case PL_EXTERNVALUE:
      cpDestroy( (CustomPayload*)this );
      break;
    default:
      free( this );
  }
}

edgepayload_t
epGetType( EdgePayload* this ) {
    return this->type;
}

State*
epWalk( EdgePayload* this, State* params ) {
  if( !this )
    return NULL;

  switch( this->type ) {
    case PL_STREET:
      return streetWalk( (Street*)this, params );
    case PL_TRIPHOPSCHED:
      return thsWalk((TripHopSchedule*)this, params);
    case PL_TRIPHOP:
      return triphopWalk((TripHop*)this, params );
    case PL_LINK:
      return linkWalk((Link*)this, params);
    case PL_EXTERNVALUE:
      return cpWalk( (CustomPayload*)this, params );
      break;
    default:
      return NULL;
  }
}

State*
epWalkBack( EdgePayload* this, State* params ) {
  if(!this)
    return NULL;

  switch( this->type ) {
    case PL_STREET:
      return streetWalkBack( (Street*)this, params );
    case PL_TRIPHOPSCHED:
      return thsWalkBack( (TripHopSchedule*)this, params );
    case PL_TRIPHOP:
      return triphopWalkBack( (TripHop*)this, params );
    case PL_LINK:
      return linkWalkBack( (Link*)this, params );
    case PL_EXTERNVALUE:
      return cpWalkBack( (CustomPayload*)this, params );
      break;
    default:
      return NULL;
  }
}

EdgePayload*
epCollapse( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_TRIPHOPSCHED:
      return (EdgePayload*)thsCollapse( (TripHopSchedule*)this, params) ;
    case PL_EXTERNVALUE:
      return (EdgePayload*)cpCollapse( (CustomPayload*)this, params );
    default:
      return (EdgePayload*)this;
  }
}

EdgePayload*
epCollapseBack( EdgePayload* this, State* params ) {
  switch( this->type ) {
    case PL_TRIPHOPSCHED:
      return (EdgePayload*)thsCollapseBack( (TripHopSchedule*)this, params);
    case PL_EXTERNVALUE:
      return (EdgePayload*)cpCollapseBack( (CustomPayload*)this, params );
    default:
      return (EdgePayload*)this;
  }
}

//EdgePayload*
//epCollapse( EdgePayload* this, State* param );

//EdgePayload*
//epCollapseBack( EdgePayload* this, State* param );

//LINK FUNCTIONS
Link*
linkNew( void ) {
  Link* ret = (Link*)malloc(sizeof(Link));
  ret->type = PL_LINK;
  ret->name = (char*)malloc(5*sizeof(char));
  strcpy(ret->name, "LINK");

  return ret;
}

void
linkDestroy(Link* tokill) {
  free( tokill->name );
  free( tokill );
}

char*
linkGetName(Link* this) {
    return this->name;
}

//STREET FUNCTIONS
Street*
streetNew(const char *name, double length) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->type = PL_STREET;
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

char*
streetGetName(Street* this) {
    return this->name;
}

double
streetGetLength(Street* this) {
    return this->length;
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
  ret->type = PL_TRIPHOPSCHED;
  ret->hops = (TripHop*)malloc(n*sizeof(TripHop));
  ret->n = n;
  ret->service_id = service_id;
  ret->calendar = calendar;
  ret->timezone_offset = timezone_offset;

  int i;
  for(i=0; i<n; i++) {
    ret->hops[i].type = PL_TRIPHOP;
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
	/* Possible leak with unfreed trip_id
    int i;
  	for(i=0; i<this->n; i++) {
  		triphopDestroy(this->hops[i]);
  	}
  	*/
  	free(this->hops);
  	free(this);
}

void

triphopDestroy(TripHop* tokill) {
  free(tokill->trip_id);
  free(tokill);
}

int
thsGetN(TripHopSchedule* this) {
    return this->n;
}

ServiceId
thsGetServiceId(TripHopSchedule* this) {
    return this->service_id;
}

int
triphopDepart( TripHop* this ) { return this->depart; }

int
triphopArrive( TripHop* this ) { return this->arrive; }

int
triphopTransit( TripHop* this ) { return this->transit; }

char *
triphopTripId( TripHop* this ) { return this->trip_id; }

TripHop*
thsGetHop(TripHopSchedule* this, int i) { return &this->hops[i]; }


// CUSTOM Payload Functions

PayloadMethods*
defineCustomPayloadType(void (*destroy)(void*),
						State* (*walk)(void*,State*),
						State* (*walkback)(void*,State*),
						EdgePayload* (*collapse)(void*,State*),
						EdgePayload* (*collapseBack)(void*,State*)) {
	PayloadMethods* this = (PayloadMethods*)malloc(sizeof(PayloadMethods));
	this->destroy = destroy;
	this->walk = walk;
	this->walkBack = walkback;
	this->collapse = collapse;
	this->collapseBack = collapseBack;
	return this;
}

void 
undefineCustomPayloadType( PayloadMethods* this ) {
	free(this);	
}

CustomPayload*
cpNew( void* soul, PayloadMethods* methods ) {
	CustomPayload* this = (CustomPayload*)malloc(sizeof(CustomPayload));
	this->type = PL_EXTERNVALUE;
	this->soul = soul;
	this->methods = methods;
	return this;
}

void
cpDestroy( CustomPayload* this ) {
	this->methods->destroy(this->soul);
	free( this );
}

void*
cpSoul( CustomPayload* this ) {
	return this->soul;
}

PayloadMethods*
cpMethods( CustomPayload* this ) {
	return this->methods;
}

State*
cpWalk(CustomPayload* this, State* params) {
	return this->methods->walk(this->soul, params);	
}
State*
cpWalkBack(CustomPayload* this, State* params) {
	return this->methods->walkBack(this->soul, params);	
}

EdgePayload*
cpCollapse(CustomPayload* this, State* params) {
	if (this->methods->collapse)
		return this->methods->collapse(this->soul, params);
	return (EdgePayload*)this;	
}

EdgePayload*
cpCollapseBack(CustomPayload* this, State* params) {
	if (this->methods->collapseBack)
		return this->methods->collapseBack(this->soul, params);
	return (EdgePayload*)this;	
}

#undef ROUTE_REVERSE
#include "edgeweights.c"
#define ROUTE_REVERSE
#include "edgeweights.c"
#undef ROUTE_REVERSE
