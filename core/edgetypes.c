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
    case PL_HEADWAY:
      headwayDestroy( (Headway*)this );
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

  if( this->type == PL_EXTERNVALUE ) {
    return cpWalk( (CustomPayload*)this, params );
  }
  
  return this->walk( this, params, transferPenalty );

}

State*
epWalkBack( EdgePayload* this, State* params, int transferPenalty ) {
  if(!this)
    return NULL;

  if( this->type == PL_EXTERNVALUE ){
    return cpWalkBack( (CustomPayload*)this, params );
  }
  
  return this->walkBack( this, params, transferPenalty );
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
    
  //bind functions to methods
  ret->walk = &linkWalk;
  ret->walkBack = &linkWalkBack;

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

int
linkReturnOne(Link* this) {
    return 1;
}

//STREET FUNCTIONS
Street*
streetNew(const char *name, double length) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->type = PL_STREET;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
    
  //bind functions to methods
  ret->walk = &streetWalk;
  ret->walkBack = &streetWalkBack;

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
waitNew(long end, Timezone* timezone) {
    Wait* ret = (Wait*)malloc(sizeof(Wait));
    ret->type = PL_WAIT;
    ret->end = end;
    ret->timezone = timezone;
    
    ret->walk = waitWalk;
    ret->walkBack = waitWalkBack;
    
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

Timezone*
waitGetTimezone(Wait* this) {
    return this->timezone;
}

//HEADWAY FUNCTIONS

Headway*
headwayNew(int begin_time, int end_time, int wait_period, int transit, char* trip_id, ServiceCalendar* calendar, Timezone* timezone, int agency, ServiceId service_id) {
    Headway* ret = (Headway*)malloc(sizeof(Headway));
    
    ret->type = PL_HEADWAY;
    ret->begin_time = begin_time;
    ret->end_time = end_time;
    ret->wait_period = wait_period;
    ret->transit = transit;
    int n = strlen(trip_id)+1;
    ret->trip_id = (char*)malloc(sizeof(char)*(n));
    memcpy(ret->trip_id, trip_id, n);
    ret->calendar = calendar;
    ret->timezone = timezone;
    ret->agency = agency;
    ret->service_id = service_id;
    
    //bind functions to methods
    ret->walk = &headwayWalk;
    ret->walkBack = &headwayWalkBack;
    
    return ret;
}

void
headwayDestroy(Headway* tokill) {
  free(tokill->trip_id);
  free(tokill);
}

int
headwayBeginTime(Headway* this) { return this->begin_time; }

int
headwayEndTime(Headway* this) { return this->end_time; }

int
headwayWaitPeriod(Headway* this) { return this->wait_period; }

int
headwayTransit(Headway* this) { return this->transit; }

char*
headwayTripId(Headway* this) { return this->trip_id; }

ServiceCalendar*
headwayCalendar(Headway* this) { return this->calendar; }

Timezone*
headwayTimezone(Headway* this) { return this->timezone; }

int
headwayAgency(Headway* this) { return this->agency; }

ServiceId
headwayServiceId(Headway* this) { return this->service_id; }

//TRIPBOARD FUNCTIONS

TripBoard*
tbNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  TripBoard* ret = (TripBoard*)malloc(sizeof(TripBoard));
  ret->type = PL_TRIPBOARD;
  ret->n = 0;
  ret->departs = NULL;
  ret->trip_ids = NULL;
    
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;
  ret->service_id = service_id;
    
  ret->walk = &tbWalk;
    
  return ret;
}

void
tbDestroy(TripBoard* this) {
  int i;
  for(i=0; i<this->n; i++) {
    free(this->trip_ids[i]);
  }
  if(this->trip_ids) {
    free(this->trip_ids);
  }
  if(this->departs){
    free(this->departs);
  }
  free( this );
}

ServiceCalendar*
tbGetCalendar( TripBoard* this ) {
  return this->calendar;
}

Timezone*
tbGetTimezone( TripBoard* this ) {
  return this->timezone;
}

int
tbGetAgency( TripBoard* this ) {
  return this->agency;
}

ServiceId
tbGetServiceId( TripBoard* this ) {
  return this->service_id;
}

int
tbGetNumBoardings(TripBoard* this) {
  return this->n;
}

void
tbAddBoarding(TripBoard* this, char* trip_id, int depart) {
    
    
    // init the trip_id, depart list
    if(this->n==0) {
        this->departs = (int*)malloc(sizeof(int));
        this->trip_ids = (char**)malloc(sizeof(char*));
        
        this->departs[0] = depart;
        
        int n = strlen(trip_id)+1;
        this->trip_ids[0] = (char*)malloc(sizeof(char)*(n));
        memcpy(this->trip_ids[0], trip_id, n);
        
    } else {
        //allocate new, expanded lists with size enough for the extra departure
        int* next_departs = (int*)malloc((this->n+1)*sizeof(int));
        char** next_trip_ids = (char**)malloc((this->n+1)*sizeof(char*));
        
        //find insertion point
        int m = tbSearchBoardingsList(this, depart);
        
        //copy old list to new list up to insertion point
        int i;
        for(i=0; i<m; i++) {
            next_departs[i] = this->departs[i];
            next_trip_ids[i] = this->trip_ids[i];
        }
        
        //copy new departure into lists
        next_departs[m] = depart;
        int strn = strlen(trip_id)+1;
        next_trip_ids[m] = (char*)malloc(sizeof(char)*(strn));
        memcpy(next_trip_ids[m], trip_id, strn);
        
        //copy old list to new list from insertion point on
        for(i=m; i<this->n; i++) {
            next_departs[i+1] = this->departs[i];
            next_trip_ids[i+1] = this->trip_ids[i];
        }
        
        //free and replace old lists
        free(this->departs);
        free(this->trip_ids);
        this->departs = next_departs;
        this->trip_ids = next_trip_ids;
    }
    
    this->n += 1;
}

char*
tbGetBoardingTripId(TripBoard* this, int i) {
    if(i<0 || i >= this->n) {
        return NULL;
    }
    
    return this->trip_ids[i];
}

int
tbGetBoardingDepart(TripBoard* this, int i) {
    if(i<0 || i >= this->n) {
        return -1;
    }
    
    return this->departs[i];
}

int
tbSearchBoardingsList(TripBoard* this, int time) {
    int first = 0;
    int last = this->n-1;
    int mid; 
    
    //fprintf( stderr, "first, last: %d, %d", first, last );
    
    while( first <= last ) {
        mid = (first+last)/2;
        //fprintf( stderr, "first: %d last: %d mid: %d\n", first, last, mid );
        if( time > this->departs[mid] ) {
            first = mid+1;
            //fprintf( stderr, "time above searchspan mid; setting first to %d\n", first );
        } else if( time < this->departs[mid] ) {
            last = mid-1;
            //fprintf( stderr, "time below searchspan mid; setting last to %d\n", last );
        } else {
            //fprintf( stderr, "time is mid; setting last to %d\n\n", last );
            return mid;
        }
    }
    
    //fprintf( stderr, "not found, returning first: %d\n\n", first );
    return first;
}

int
tbGetNextBoardingIndex(TripBoard* this, int time) {
    int index = tbSearchBoardingsList( this, time );
    
    if( index == this->n ) { //insertion point beyond end of array, return error code
        return -1;
    }
    
    return index;
}

inline State*
tbWalk( EdgePayload* superthis, State* params, int transferPenalty ) {
    TripBoard* this = (TripBoard*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrAfter( this->calendar, params->time );
        params->service_periods[this->agency] = service_period;
    
    // if the schedule never runs
    // or if the schedule does not run on this day
    // this link goes nowhere
    if( !service_period ||
        !spPeriodHasServiceId( service_period, this->service_id) ) {
      return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( params );
    
    ret->num_transfers += 1;
    
    long adjusted_time = spNormalizeTime( service_period, tzUtcOffset(this->timezone, params->time), params->time );
    
    int next_boarding_index = tbGetNextBoardingIndex( this, adjusted_time );
    
    if( next_boarding_index == -1 ) {
        return NULL;
    }
    
    int next_boarding_time = this->departs[next_boarding_index];
    int wait = (next_boarding_time - adjusted_time);
    
    ret->time   += wait;
    ret->weight += wait + 1; //transfer penalty
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

// CROSSING FUNCTIONS

Crossing*
crNew( int crossing_time ) {
  Crossing* ret = (Crossing*)malloc(sizeof(Crossing));
  ret->type = PL_CROSSING;
  ret->crossing_time = crossing_time;
    
  ret->walk = &crWalk;
    
  return ret;
}

void
crDestroy(Crossing* this) {
  free(this);
}

int
crGetCrossingTime(Crossing* this) {
  return this->crossing_time;
}

inline State*
crWalk( EdgePayload* superthis, State* params, int transferPenalty ) {
    Crossing* this = (Crossing*)superthis;
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( params );
    
    ret->time   += this->crossing_time;
    ret->weight += this->crossing_time;
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

// ALIGHT FUNCTIONS

Alight*
alNew() {
    Alight* ret = (Alight*)malloc(sizeof(Alight));
    ret->type = PL_ALIGHT;
    
    ret->walk = &alWalk;
    
    return ret;
}

void
alDestroy(Alight* this) {
    free(this);
}

inline State*
alWalk(EdgePayload* this, State* params, int transferPenalty) {
    return stateDup( params );
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
  
  //bind functions to methods
  ret->walk = &thsWalk;
  ret->walkBack = &thsWalkBack;

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
    
  //bind functions to methods
  ret->walk = &triphopWalk;
  ret->walkBack = &triphopWalkBack;
    
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
