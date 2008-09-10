#include "edgetypes.h"
#include "math.h"
#include <stdio.h>

//STATE FUNCTIONS
State*
stateNew(int n_agencies, long time) {
  State* ret = (State*)malloc( sizeof(State) );
  ret->time = time;
  ret->weight = 0;
  ret->dist_walked = 0;
  ret->num_transfers = 0;
  ret->prev_edge_name = NULL;
  ret->prev_edge_type = PL_NONE;
  ret->n_agencies = n_agencies;
  ret->service_periods = (ServicePeriod**)malloc(n_agencies*sizeof(ServicePeriod*)); //hash of strings->calendardays

  int i;
  for(i=0; i<n_agencies; i++) {
      ret->service_periods[i] = NULL;
  }

  return ret;
}

State*
stateDup( State* this ) {
  State* ret = (State*)malloc( sizeof(State) );
  memcpy( ret, this, sizeof( State ) );

  ret->service_periods = (ServicePeriod**)malloc(this->n_agencies*sizeof(ServicePeriod*)); //hash of strings->calendardays
  memcpy( ret->service_periods, this->service_periods, this->n_agencies*sizeof(ServicePeriod*));

  return ret;
}

//the State object does not own State#calendar
void
stateDestroy(State* this) {
  free( this->service_periods );
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

int
stateGetNumAgencies( State* this ) { return this->n_agencies; }

ServicePeriod*
stateServicePeriod( State* this, int agency ) { return this->service_periods[agency]; }

void
stateSetTime( State* this, long time ) { this->time = time; }

void
stateSetWeight( State* this, long weight ) { this->weight = weight; }

void
stateSetDistWalked( State* this, double dist ) { this->dist_walked = dist; }

void
stateSetNumTransfers( State* this, int n) { this->num_transfers = n; }

void
stateSetServicePeriod( State* this,  int agency, ServicePeriod* cal ) { this->service_periods[agency] = cal; }

void
stateSetPrevEdgeName( State* this, char* name ) { this->prev_edge_name = name; }

void
stateSetPrevEdgeType( State* this, edgepayload_t type ) { this->prev_edge_type = type; }

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
    case PL_WAIT:
      waitDestroy( (Wait*)this );
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
epWalk( EdgePayload* this, State* params, int transferPenalty ) {
  if( !this )
    return NULL;

  switch( this->type ) {
    case PL_STREET:
      return streetWalk( (Street*)this, params );
    case PL_TRIPHOPSCHED:
      return thsWalk((TripHopSchedule*)this, params, transferPenalty);
    case PL_TRIPHOP:
      return triphopWalk((TripHop*)this, params, transferPenalty );
    case PL_LINK:
      return linkWalk((Link*)this, params);
    case PL_EXTERNVALUE:
      return cpWalk( (CustomPayload*)this, params );
      break;
    case PL_WAIT:
      return waitWalk( (Wait*)this, params, transferPenalty );
      break;
    default:
      return NULL;
  }
}

State*
epWalkBack( EdgePayload* this, State* params, int transferPenalty ) {
  if(!this)
    return NULL;

  switch( this->type ) {
    case PL_STREET:
      return streetWalkBack( (Street*)this, params );
    case PL_TRIPHOPSCHED:
      return thsWalkBack( (TripHopSchedule*)this, params, transferPenalty );
    case PL_TRIPHOP:
      return triphopWalkBack( (TripHop*)this, params, transferPenalty );
    case PL_LINK:
      return linkWalkBack( (Link*)this, params );
    case PL_EXTERNVALUE:
      return cpWalkBack( (CustomPayload*)this, params );
    case PL_WAIT:
      return waitWalkBack( (Wait*)this, params, transferPenalty );
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
linkNew() {
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

//WAIT FUNCTIONS
Wait*
waitNew(long end, int utcoffset) {
    Wait* ret = (Wait*)malloc(sizeof(Wait));
    ret->type = PL_WAIT;
    ret->end = end;
    ret->utcoffset = utcoffset;
    
    return ret;
}

void
waitDestroy(Wait* tokill) {
    free(tokill);
}

long
waitGetEnd(Wait* this) {
    return this->end;
}

int
waitGetUTCOffset(Wait* this) {
    return this->utcoffset;
}

//TRIPHOP FUNCTIONS

//tests the order of the hops, by terminus time, for use with sorting functions
int hopcmp(const void* a, const void* b) {
  TripHop** aa = (TripHop**)a;
  TripHop** bb = (TripHop**)b;
  
  TripHop* ac = *aa;
  TripHop* bc = *bb;
  if(ac->arrive < bc->arrive)
    return -1;
  else if(ac->arrive > bc->arrive)
    return 1;
  else {
    return 0;
  }
}

/*
 * Receives n tuples consisting if [depart, arrive, trip_id], all associated with one service_id
 */

TripHopSchedule*
thsNew( int *departs, int *arrives, char **trip_ids, int n, ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  TripHopSchedule* ret = (TripHopSchedule*)malloc(sizeof(TripHopSchedule));
  ret->type = PL_TRIPHOPSCHED;
  ret->hops = (TripHop**)malloc(n*sizeof(TripHop*));
  ret->n = n;
  ret->service_id = service_id;
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;

  int i;
  for(i=0; i<n; i++) {
    ret->hops[i] = triphopNew( departs[i], arrives[i], trip_ids[i], calendar, timezone, agency, service_id );
  }

  //make sure departure and arrival arrays are sorted, as they're subjected to a binsearch
  qsort(ret->hops, n, sizeof(TripHop*), hopcmp);

  return ret; // return NULL;
}

TripHop*
triphopNew(int depart, int arrive, char* trip_id, ServiceCalendar* calendar, Timezone* timezone, int agency, ServiceId service_id) {
    TripHop* ret = (TripHop*)malloc(sizeof(TripHop));
    
    ret->type = PL_TRIPHOP;
    ret->depart = depart;
    ret->arrive = arrive;
    ret->transit = (arrive-depart);
    int n = strlen(trip_id)+1;
    ret->trip_id = (char*)malloc(sizeof(char)*(n));
    memcpy(ret->trip_id, trip_id, n);
    ret->calendar = calendar;
    ret->timezone = timezone;
    ret->agency = agency;
    ret->service_id = service_id;
    
    return ret;
}

//GEOM FUNTIONS

Geom*
geomNew (char * geomdata) {

        if (geomdata==NULL)
		return NULL;
	Geom* tmp=(Geom *)malloc(sizeof(Geom));
        tmp->data=strdup(geomdata);
	return tmp;
}

void
geomDestroy(Geom* this){

	if (this!=NULL)
	{
		if (this->data!=NULL) free(this->data);
		free(this);
		this=NULL;
	}
}


//COORDINATES FUNTIONS
Coordinates*
coordinatesNew(long latitude,long length)
{
	Coordinates* ret=(Coordinates*)malloc(sizeof(Coordinates));
	ret->lat=latitude;
	ret->lon=length;
	return ret;
}

void
coordinatesDestroy(Coordinates* this){
	if (this!=NULL) free(this);
}

Coordinates*
coordinatesDup(Coordinates* this) {
	Coordinates* ret=(Coordinates*)malloc(sizeof(Coordinates));
	memcpy(ret,this,sizeof( Coordinates ));
	return ret;
}

//DEBUG CODE
void
thsPrintHops(TripHopSchedule* this) {
  int i;
  printf("--==--\n");
  for(i=0; i<this->n; i++) {
    printf("Hop: %d, %d, %s\n", this->hops[i]->depart, this->hops[i]->arrive, this->hops[i]->trip_id);
  }
  printf("--==--\n");
}

void
thsDestroy(TripHopSchedule* this) {
    int i;
  	for(i=0; i<this->n; i++) {
        //free( this->hops[i]->trip_id );
        triphopDestroy(this->hops[i]);
  	}

  	free(this->hops);
  	free(this);
}

ServiceCalendar*
thsGetCalendar(TripHopSchedule* this ) { return this->calendar; }

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

Timezone*
thsGetTimezone(TripHopSchedule* this) {
    return this->timezone;
}

int
triphopDepart( TripHop* this ) { return this->depart; }

int
triphopArrive( TripHop* this ) { return this->arrive; }

int
triphopTransit( TripHop* this ) { return this->transit; }

char *
triphopTripId( TripHop* this ) { return this->trip_id; }

ServiceCalendar*
triphopCalendar( TripHop* this ) { return this->calendar; }

Timezone*
triphopTimezone( TripHop* this ) { return this->timezone; }

int
triphopAuthority( TripHop* this ) { return this->agency; }

int
triphopServiceId( TripHop* this ) { return this->service_id; }

TripHop*
thsGetHop(TripHopSchedule* this, int i) { return this->hops[i]; }


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
	State* s = this->methods->walk(this->soul, params);
	s->prev_edge_type = PL_EXTERNVALUE;
	return s;
}
State*
cpWalkBack(CustomPayload* this, State* params) {
	State* s = this->methods->walkBack(this->soul, params);
	s->prev_edge_type = PL_EXTERNVALUE;
	return s;
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
