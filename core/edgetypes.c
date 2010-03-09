#include "edgetypes.h"
#include "edgetypes/link.h"
#include "edgetypes/street.h"
#include "edgetypes/egress.h"
#include "edgetypes/wait.h"
#include "edgetypes/elapsetime.h"
#include "edgetypes/headway.h"
#include "edgetypes/tripboard.h"
#include "edgetypes/headwayboard.h"
#include "edgetypes/headwayalight.h"
#include "edgetypes/crossing.h"
#include "math.h"
#include <stdio.h>

//---------------DEFINITIONS FOR WALKOPTIONS CLASS---------------

WalkOptions*
woNew() {
    WalkOptions* ret = (WalkOptions*)malloc( sizeof(WalkOptions) );
    ret->transfer_penalty = 0;
    ret->turn_penalty = 0;
    ret->walking_speed = 6.07; //meters per second
    ret->walking_reluctance = 1;
    ret->uphill_slowness = 0.05; //Factor by which someone's speed is slowed going uphill.
    ret->downhill_fastness = -12.1; // meters per second per grade percentage
    ret->phase_change_grade = 0.045; // Grade. An interesting thing happens at a particular grade, when they settle in for a long slog.
    ret->hill_reluctance = 0; //Factor by which an uphill stretch is penalized, in addition to whatever time is lost by simply gaining.
    ret->max_walk = 10000; //meters
    ret->walking_overage = 0.1;
    
    // velocity between 0 grade and the phase change grade is Ax^2+Bx+C, where A is the phase_change_velocity_factor, B is the downhill fastness, and C is the average speed
    float phase_change_speed = (ret->uphill_slowness*ret->walking_speed)/(ret->uphill_slowness+ret->phase_change_grade);
    ret->phase_change_velocity_factor = (phase_change_speed - ret->downhill_fastness*ret->phase_change_grade - ret->walking_speed)/(ret->phase_change_grade*ret->phase_change_grade);
        
    return ret;
}

void
woDestroy( WalkOptions* this ) {
    free(this);
}

int
woGetTransferPenalty( WalkOptions* this ) {
    return this->transfer_penalty;
}

void
woSetTransferPenalty( WalkOptions* this, int transfer_penalty ) {
    this->transfer_penalty = transfer_penalty;
}

float
woGetWalkingSpeed( WalkOptions* this ) {
    return this->walking_speed;
}

void
woSetWalkingSpeed( WalkOptions* this, float walking_speed ) {
    this->walking_speed = walking_speed;
}

float
woGetWalkingReluctance( WalkOptions* this ) {
    return this->walking_reluctance;
}

void
woSetWalkingReluctance( WalkOptions* this, float walking_reluctance ) {
    this->walking_reluctance = walking_reluctance;
}

float
woGetUphillSlowness( WalkOptions* this ) {
    return this->uphill_slowness;
}

void
woSetUphillSlowness( WalkOptions* this, float uphill_slowness ) {
    this->uphill_slowness = uphill_slowness;
}

float
woGetDownhillFastness( WalkOptions* this ) {
    return this->downhill_fastness;
}

void
woSetDownhillFastness( WalkOptions* this, float downhill_fastness ) {
    this->downhill_fastness = downhill_fastness;
}

float
woGetHillReluctance( WalkOptions* this ) {
    return this->hill_reluctance;
}

void
woSetHillReluctance( WalkOptions* this, float hill_reluctance ) {
    this->hill_reluctance = hill_reluctance;
}

int
woGetMaxWalk( WalkOptions* this ) {
    return this->max_walk;
}

void
woSetMaxWalk( WalkOptions* this, int max_walk ) {
    this->max_walk = max_walk;
}

float
woGetWalkingOverage( WalkOptions* this ) {
    return this->walking_overage;
}

void
woSetWalkingOverage( WalkOptions* this, float walking_overage ) {
    this->walking_overage = walking_overage;
}

int
woGetTurnPenalty( WalkOptions* this ) {
    return this->turn_penalty;
}

void
woSetTurnPenalty( WalkOptions* this, int turn_penalty ) {
    this->turn_penalty = turn_penalty;
}

//STATE FUNCTIONS
State*
stateNew(int n_agencies, long time) {
  State* ret = (State*)malloc( sizeof(State) );
  ret->time = time;
  ret->weight = 0;
  ret->dist_walked = 0;
  ret->num_transfers = 0;
  ret->trip_id = NULL;
  ret->stop_sequence = -1;
  ret->prev_edge = NULL;
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

EdgePayload*
stateGetPrevEdge( State* this ) { return this->prev_edge; }

char*
stateGetTripId( State* this ) { return this->trip_id; }

int
stateGetStopSequence( State* this ) { return this->stop_sequence; }

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

// the state does not keep ownership of the trip_id, so the state
// may not live longer than whatever object set its trip_id
void
stateDangerousSetTripId( State* this, char* trip_id ) { this->trip_id = trip_id; }

void
stateSetPrevEdge( State* this, EdgePayload* edge ) { this->prev_edge = edge; }

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
    default:
      free( this );
  }
}

edgepayload_t
epGetType( EdgePayload* this ) {
    return this->type;
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


// ALIGHT FUNCTIONS

Alight*
alNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  Alight* ret = (Alight*)malloc(sizeof(Alight));
  ret->type = PL_ALIGHT;
  ret->n = 0;
  ret->arrivals = NULL;
  ret->trip_ids = NULL;
  ret->stop_sequences = NULL;
    
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;
  ret->service_id = service_id;
    
  ret->walk = &alWalk;
  ret->walkBack = &alWalkBack;
    
  ret->overage = 0;
    
  return ret;
}

void
alDestroy(Alight* this) {
  int i;
  for(i=0; i<this->n; i++) {
    free(this->trip_ids[i]);
  }
  if(this->trip_ids) {
    free(this->trip_ids);
  }
  if(this->arrivals){
    free(this->arrivals);
  }
  if(this->stop_sequences){
    free(this->stop_sequences);
  }
  free( this );
}

ServiceCalendar*
alGetCalendar( Alight* this ) {
  return this->calendar;
}

Timezone*
alGetTimezone( Alight* this ) {
  return this->timezone;
}

int
alGetAgency( Alight* this ) {
  return this->agency;
}

ServiceId
alGetServiceId( Alight* this ) {
  return this->service_id;
}

int
alGetNumAlightings( Alight* this) {
  return this->n;
}

void
alAddAlighting(Alight* this, char* trip_id, int arrival, int stop_sequence) {
    if (arrival > SECS_IN_DAY+this->overage)
        this->overage = arrival-SECS_IN_DAY;
    
    // init the trip_id, depart list
    if(this->n==0) {
        this->arrivals = (int*)malloc(sizeof(int));
        this->trip_ids = (char**)malloc(sizeof(char*));
        this->stop_sequences = (int*)malloc(sizeof(int));
        
        this->arrivals[0] = arrival;
        this->stop_sequences[0] = stop_sequence;
        
        int n = strlen(trip_id)+1;
        this->trip_ids[0] = (char*)malloc(sizeof(char)*(n));
        memcpy(this->trip_ids[0], trip_id, n);
        
    } else {
        //allocate new, expanded lists with size enough for the extra departure
        int* next_arrivals = (int*)malloc((this->n+1)*sizeof(int));
        char** next_trip_ids = (char**)malloc((this->n+1)*sizeof(char*));
        int* next_stop_sequences = (int*)malloc((this->n+1)*sizeof(int));
        
        //find insertion point
        int m = alSearchAlightingsList(this, arrival);
        
        //copy old list to new list up to insertion point
        int i;
        for(i=0; i<m; i++) {
            next_arrivals[i] = this->arrivals[i];
            next_trip_ids[i] = this->trip_ids[i];
            next_stop_sequences[i] = this->stop_sequences[i];
        }
        
        //copy new departure into lists
        next_arrivals[m] = arrival;
        int strn = strlen(trip_id)+1;
        next_trip_ids[m] = (char*)malloc(sizeof(char)*(strn));
        memcpy(next_trip_ids[m], trip_id, strn);
        next_stop_sequences[m] = stop_sequence;
        
        //copy old list to new list from insertion point on
        for(i=m; i<this->n; i++) {
            next_arrivals[i+1] = this->arrivals[i];
            next_trip_ids[i+1] = this->trip_ids[i];
            next_stop_sequences[i+1] = this->stop_sequences[i];
        }
        
        //free and replace old lists
        free(this->arrivals);
        free(this->trip_ids);
        free(this->stop_sequences);
        this->arrivals = next_arrivals;
        this->trip_ids = next_trip_ids;
        this->stop_sequences = next_stop_sequences;
    }
    
    this->n += 1;
}

char*
alGetAlightingTripId(Alight* this, int i) {
    if(i<0 || i >= this->n) {
        return NULL;
    }
    
    return this->trip_ids[i];
}

int
alGetAlightingArrival(Alight* this, int i) {
    if(i<0 || i >= this->n) {
        return -1;
    }
    
    return this->arrivals[i];
}

int
alGetAlightingStopSequence(Alight* this, int i) {
    if(i<0 || i >= this->n) {
        return -1;
    }
    
    return this->stop_sequences[i];
}

int
binsearch(int* ary, int n, int key, int before) {
    int first = 0;
    int last = n-1;
    int mid; 
    
    while( first <= last ) {
        mid = (first+last)/2;
        if( key > ary[mid] ) {
            first = mid+1;
        } else if( key < ary[mid] ) {
            last = mid-1;
        } else {
            return mid;
        }
    }
    
    return first-before;
}

int
alSearchAlightingsList(Alight* this, int time) {
    return binsearch( this->arrivals, this->n, time, 0);
}

int
alGetLastAlightingIndex(Alight* this, int time) {
    //if insertion point is before end of array, -1 will be returned, which is coincidentally the error code
    return binsearch( this->arrivals, this->n, time, 1 );
}

int
alGetOverage(Alight* this) {
    return this->overage;
}

int
alGetAlightingIndexByTripId(Alight* this, char* trip_id) {
    /* returns the boarding index of the alighting with the given trip_id */
    
    int i;
    for(i=0; i<this->n; i++) {
        if( strcmp(this->trip_ids[i], trip_id)==0 ) {
            return i;
        }
    }
    
    return -1; 
}

inline State*
alWalk(EdgePayload* this, State* state, WalkOptions* options) {
    State* ret = stateDup( state );
    ret->trip_id = NULL;
    
    return ret;
}

inline State*
alWalkBack( EdgePayload* superthis, State* state, WalkOptions* options ) {
    Alight* this = (Alight*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrBefore( this->calendar, state->time );
        state->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, state->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, state->time );
        
    if( !spPeriodHasServiceId( service_period, this->service_id ) ) {
        
        /* If the boarding schedule extends past midnight - for example, you can board a train on the Friday schedule until
         * 2 AM Saturday morning - and the travel_state.time_since_midnight is less than this overage - for example, 1 AM, but
         * the travel_state.service_period will show Saturday and not Friday, then:
         * 
         * Check if the boarding schedule service_id is running in the travel_state's yesterday period. If it is, simply advance the 
         * time_since_midnight by a day and continue. If not, this boarding schedule was not running today or yesterday, so as far
         * as we're concerned, it's not running at all
         *
         * TODO - figure out an algorithm for the general cse
         */
        
        if( service_period->prev_period &&
            spPeriodHasServiceId( service_period->prev_period, this->service_id )) {
                
            time_since_midnight += SECS_IN_DAY;
        } else {
            return NULL;
        }
        
    }
    
    int last_alighting_index = alGetLastAlightingIndex( this, time_since_midnight );
    
    if( last_alighting_index == -1 ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    ret->stop_sequence = this->stop_sequences[last_alighting_index];
    
    ret->num_transfers += 1;
    
    int last_alighting_time = this->arrivals[last_alighting_index];
    int wait = (time_since_midnight - last_alighting_time);
    
    ret->time   -= wait;
    ret->weight += wait + 1; //transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_ids[last_alighting_index];
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
          ret->service_periods[i] = ret->service_periods[i]->prev_period;
        }
    }
    
    return ret;
    
}

// CUSTOM Payload Functions

PayloadMethods*
defineCustomPayloadType(void (*destroy)(void*),
						State* (*walk)(void*,State*,WalkOptions*),
						State* (*walkback)(void*,State*,WalkOptions*)) {
	PayloadMethods* this = (PayloadMethods*)malloc(sizeof(PayloadMethods));
	this->destroy = destroy;
	this->walk = walk;
	this->walkBack = walkback;
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
cpWalk(CustomPayload* this, State* state, WalkOptions* walkoptions) {
	State* s = this->methods->walk(this->soul, state, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}
State*
cpWalkBack(CustomPayload* this, State* state, WalkOptions* walkoptions) {
	State* s = this->methods->walkBack(this->soul, state, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}

#undef ROUTE_REVERSE
#include "edgeweights.c"
#define ROUTE_REVERSE
#include "edgeweights.c"
#undef ROUTE_REVERSE
