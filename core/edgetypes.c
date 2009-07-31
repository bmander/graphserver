#include "edgetypes.h"
#include "math.h"
#include <stdio.h>

//---------------DEFINITIONS FOR WALKOPTIONS CLASS---------------

WalkOptions*
woNew() {
    WalkOptions* ret = (WalkOptions*)malloc( sizeof(WalkOptions) );
    ret->transfer_penalty = 0;
    ret->turn_penalty = 0;
    ret->walking_speed = 0.85; //meters per second
    ret->walking_reluctance = 1;
    ret->uphill_slowness = 0.08; //Factor by which someone's speed is slowed going uphill. A 15 mph rider on a flat will climb at 1.2 mph, for example.
    ret->downhill_fastness = 1.96; // s/m. Number of seconds regained for every foot dropped. 10 feet dropped will gain you six seconds.
    ret->hill_reluctance = 1.5; //Factor by which an uphill stretch is penalized, in addition to whatever time is lost by simply gaining.
    ret->max_walk = 10000; //meters
    ret->walking_overage = 0.1;
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
epWalk( EdgePayload* this, State* params, WalkOptions* options ) {
  if( !this )
    return NULL;

  if( this->type == PL_EXTERNVALUE ) {
    return cpWalk( (CustomPayload*)this, params, options );
  }
  
  return this->walk( this, params, options );

}

State*
epWalkBack( EdgePayload* this, State* params, WalkOptions* options ) {
  if(!this)
    return NULL;

  if( this->type == PL_EXTERNVALUE ){
    return cpWalkBack( (CustomPayload*)this, params, options );
  }
  
  return this->walkBack( this, params, options );
}

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
  ret->rise = 0;
  ret->fall = 0;
  ret->slog = 1;
  ret->way = 0;
    
  //bind functions to methods
  ret->walk = &streetWalk;
  ret->walkBack = &streetWalkBack;

  return ret;
}

Street*
streetNewElev(const char *name, double length, float rise, float fall) {
    Street* ret = streetNew( name, length );
    ret->rise = rise;
    ret->fall = fall;
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

float
streetGetRise(Street* this) {
    return this->rise;
}

float
streetGetFall(Street* this) {
    return this->fall;
}

float
streetGetSlog(Street* this) {
    return this->slog;
}

void
streetSetSlog(Street* this, float slog) {
    this->slog = slog;
}

long
streetGetWay(Street* this) {
    return this->way;   
}

void
streetSetWay(Street* this, long way) {
    this->way = way;
}

//EGRESS FUNCTIONS
Egress*
egressNew(const char *name, double length) {
  Egress* ret = (Egress*)malloc(sizeof(Egress));
  ret->type = PL_EGRESS;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
  
  //bind functions to methods
  ret->walk = &egressWalk;
  ret->walkBack = &egressWalkBack;

  return ret;
}

void
egressDestroy(Egress* tokill) {
  free(tokill->name);
  free(tokill);
}

char*
egressGetName(Egress* this) {
    return this->name;
}

double
egressGetLength(Egress* this) {
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

//ElapseTime FUNCTIONS
ElapseTime*
elapseTimeNew(long seconds) {
    ElapseTime* ret = (ElapseTime*)malloc(sizeof(ElapseTime));
    ret->type = PL_ELAPSE_TIME;
    ret->seconds = seconds;
    
    ret->walk = elapseTimeWalk;
    ret->walkBack = elapseTimeWalkBack;
    
    return ret;
}

void
elapseTimeDestroy(ElapseTime* tokill) {
    free(tokill);
}

long
elapseTimeGetSeconds(ElapseTime* this) {
    return this->seconds;
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
  ret->walkBack = &tbWalkBack;
    
  ret->overage = 0;
    
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
    if (depart > SECS_IN_DAY+this->overage)
        this->overage = depart-SECS_IN_DAY;
    
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

int
tbGetOverage(TripBoard* this) {
    return this->overage;
}

/*
given TripBoard with service ID of friday, list of boardings going until 3 AM, and schedule, gets time corresponding to saturday at 2 AM.

The on-board service calendar would resolve 2AM to saturday to the saturday service ID, which does not match the friday service ID; the conclusion
is that the current is not in the service day served by this vehicle, and so a NULL is returned.

In fact times do run until 3 AM saturday, so you could catch any train on this TripBoard's boarding schedule between 2 AM and 3 AM.

I think the trick is for the TripBoard to realize that it should cut the State some slack, because it's going over from 2 to 3.

So the TripBoard knows the last departure is three hours after the end of the day. The TripHop can add 24 hours to the time-since-midnight of the 
State and check yesterday's schedule. The TripHop will find the next departure that way.

This appears to b e _always_ a safe thing to do. If the service day of the State does not match the TripId and the time-since-midnight of the State is
smaller than the overage of the TripBoard, roll back the day by the number of days of the overage (probably always one) and increment the state time by the same
number of days, and check again.
*/

inline State*
tbWalk( EdgePayload* superthis, State* params, WalkOptions* options ) {
    TripBoard* this = (TripBoard*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrAfter( this->calendar, params->time );
        params->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, params->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, params->time );
        
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
        
        if( this->overage >= time_since_midnight &&
            service_period->prev_period &&
            spPeriodHasServiceId( service_period->prev_period, this->service_id )) {
                
            time_since_midnight += SECS_IN_DAY;
        } else {
            return NULL;
        }
        
    }
    
    int next_boarding_index = tbGetNextBoardingIndex( this, time_since_midnight );
    
    if( next_boarding_index == -1 ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( params );
    
    ret->num_transfers += 1;
    
    int next_boarding_time = this->departs[next_boarding_index];
    int wait = (next_boarding_time - time_since_midnight);
    
    ret->time   += wait;
    ret->weight += wait + 1; //base transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_ids[next_boarding_index];
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

inline State*
tbWalkBack(EdgePayload* this, State* params, WalkOptions* options) {
    State* ret = stateDup( params );
    ret->trip_id = NULL;
    
    return ret;
}

// HEADWAYBOARD FUNCTIONS

HeadwayBoard*
hbNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs ) {
  HeadwayBoard* ret = (HeadwayBoard*)malloc(sizeof(HeadwayBoard));
  ret->type = PL_HEADWAYBOARD;

  int n = strlen(trip_id)+1;
  ret->trip_id = (char*)malloc(sizeof(char)*(n));
  memcpy(ret->trip_id, trip_id, n);
  ret->start_time = start_time;
  ret->end_time = end_time;
  ret->headway_secs = headway_secs;
    
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;
  ret->service_id = service_id;
    
  ret->walk = &hbWalk;
  ret->walkBack = &hbWalkBack;
    
  return ret;
}

void
hbDestroy(HeadwayBoard* this) {
  free( this->trip_id );
  free( this );
}

ServiceCalendar*
hbGetCalendar( HeadwayBoard* this ) {
  return this->calendar;
}

Timezone*
hbGetTimezone( HeadwayBoard* this ) {
  return this->timezone;
}

int
hbGetAgency( HeadwayBoard* this ) {
  return this->agency;
}

ServiceId
hbGetServiceId( HeadwayBoard* this ) {
  return this->service_id;
}

char*
hbGetTripId( HeadwayBoard* this ) {
  return this->trip_id;
}

int
hbGetStartTime( HeadwayBoard* this ) {
  return this->start_time;
}

int
hbGetEndTime( HeadwayBoard* this ) {
  return this->end_time;
}

int
hbGetHeadwaySecs( HeadwayBoard* this ) {
  return this->headway_secs;
}

inline State*
hbWalk( EdgePayload* superthis, State* params, WalkOptions* options ) {
    HeadwayBoard* this = (HeadwayBoard*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrAfter( this->calendar, params->time );
        params->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, params->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, params->time );
        
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
        
        if( this->end_time-SECS_IN_DAY >= time_since_midnight &&
            service_period->prev_period &&
            spPeriodHasServiceId( service_period->prev_period, this->service_id )) {
                
            time_since_midnight += SECS_IN_DAY;
        } else {
            return NULL;
        }
        
    }
    
    if (time_since_midnight > this->end_time ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( params );
    
    ret->num_transfers += 1;
    
    int wait = this->headway_secs; //you could argue the correct wait is headway_secs/2
    
    if (time_since_midnight < this->start_time )
        wait += (this->start_time - time_since_midnight);
    
    ret->time   += wait;
    ret->weight += wait + 1; //transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_id;
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

inline State*
hbWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
    HeadwayBoard* this = (HeadwayBoard*)superthis;
    
    State* ret = stateDup( params );
    
    int wait = this->headway_secs; 
    ret->time   -= wait;
    ret->weight += wait; //transfer penalty
    ret->trip_id = NULL;
    
    return ret;
}

// HEADWAYALIGHT FUNCTIONS

HeadwayAlight*
haNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs ) {
  HeadwayAlight* ret = (HeadwayAlight*)malloc(sizeof(HeadwayAlight));
  ret->type = PL_HEADWAYALIGHT;

  int n = strlen(trip_id)+1;
  ret->trip_id = (char*)malloc(sizeof(char)*(n));
  memcpy(ret->trip_id, trip_id, n);
  ret->start_time = start_time;
  ret->end_time = end_time;
  ret->headway_secs = headway_secs;
    
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;
  ret->service_id = service_id;
    
  ret->walk = &haWalk;
  ret->walkBack = &haWalkBack;
    
  return ret;
}

void
haDestroy(HeadwayAlight* this) {
  free( this->trip_id );
  free( this );
}

ServiceCalendar*
haGetCalendar( HeadwayAlight* this ) {
  return this->calendar;
}

Timezone*
haGetTimezone( HeadwayAlight* this ) {
  return this->timezone;
}

int
haGetAgency( HeadwayAlight* this ) {
  return this->agency;
}

ServiceId
haGetServiceId( HeadwayAlight* this ) {
  return this->service_id;
}

char*
haGetTripId( HeadwayAlight* this ) {
  return this->trip_id;
}

int
haGetStartTime( HeadwayAlight* this ) {
  return this->start_time;
}

int
haGetEndTime( HeadwayAlight* this ) {
  return this->end_time;
}

int
haGetHeadwaySecs( HeadwayAlight* this ) {
  return this->headway_secs;
}

inline State*
haWalk(EdgePayload* this, State* params, WalkOptions* options) {
    State* ret = stateDup( params );
    ret->trip_id = NULL;
    
    return ret;
}

inline State*
haWalkBack( EdgePayload* superthis, State* params, WalkOptions* options ) {
    HeadwayAlight* this = (HeadwayAlight*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrBefore( this->calendar, params->time );
        params->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, params->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, params->time );
        
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
    
    if (time_since_midnight < this->start_time ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( params );
    
    ret->num_transfers += 1;
    
    int wait = 0;
    
    if (time_since_midnight > this->end_time )
        wait += (time_since_midnight - this->end_time);
    
    ret->time   -= wait;
    ret->weight += wait + 1; //transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_id;
    
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
  ret->walkBack = &crWalkBack;
    
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
crWalk( EdgePayload* superthis, State* params, WalkOptions* options ) {
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

inline State*
crWalkBack( EdgePayload* superthis, State* state, WalkOptions* options ) {
    Crossing* this = (Crossing*)superthis;
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    
    ret->time   -= this->crossing_time;
    ret->weight += this->crossing_time;
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
          ret->service_periods[i] = ret->service_periods[i]->prev_period;
        }
    }
    
    return ret;
    
}

// ALIGHT FUNCTIONS

Alight*
alNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  Alight* ret = (Alight*)malloc(sizeof(Alight));
  ret->type = PL_ALIGHT;
  ret->n = 0;
  ret->arrivals = NULL;
  ret->trip_ids = NULL;
    
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
alAddAlighting(Alight* this, char* trip_id, int arrival) {
    if (arrival > SECS_IN_DAY+this->overage)
        this->overage = arrival-SECS_IN_DAY;
    
    // init the trip_id, depart list
    if(this->n==0) {
        this->arrivals = (int*)malloc(sizeof(int));
        this->trip_ids = (char**)malloc(sizeof(char*));
        
        this->arrivals[0] = arrival;
        
        int n = strlen(trip_id)+1;
        this->trip_ids[0] = (char*)malloc(sizeof(char)*(n));
        memcpy(this->trip_ids[0], trip_id, n);
        
    } else {
        //allocate new, expanded lists with size enough for the extra departure
        int* next_arrivals = (int*)malloc((this->n+1)*sizeof(int));
        char** next_trip_ids = (char**)malloc((this->n+1)*sizeof(char*));
        
        //find insertion point
        int m = alSearchAlightingsList(this, arrival);
        
        //copy old list to new list up to insertion point
        int i;
        for(i=0; i<m; i++) {
            next_arrivals[i] = this->arrivals[i];
            next_trip_ids[i] = this->trip_ids[i];
        }
        
        //copy new departure into lists
        next_arrivals[m] = arrival;
        int strn = strlen(trip_id)+1;
        next_trip_ids[m] = (char*)malloc(sizeof(char)*(strn));
        memcpy(next_trip_ids[m], trip_id, strn);
        
        //copy old list to new list from insertion point on
        for(i=m; i<this->n; i++) {
            next_arrivals[i+1] = this->arrivals[i];
            next_trip_ids[i+1] = this->trip_ids[i];
        }
        
        //free and replace old lists
        free(this->arrivals);
        free(this->trip_ids);
        this->arrivals = next_arrivals;
        this->trip_ids = next_trip_ids;
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

inline State*
alWalk(EdgePayload* this, State* params, WalkOptions* options) {
    State* ret = stateDup( params );
    ret->trip_id = NULL;
    
    return ret;
}

inline State*
alWalkBack( EdgePayload* superthis, State* params, WalkOptions* options ) {
    Alight* this = (Alight*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrBefore( this->calendar, params->time );
        params->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, params->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, params->time );
        
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
    State* ret = stateDup( params );
    
    ret->num_transfers += 1;
    
    int last_alighting_time = this->arrivals[last_alighting_index];
    int wait = (time_since_midnight - last_alighting_time);
    
    ret->time   -= wait;
    ret->weight += wait + 1; //transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_ids[last_alighting_index];
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<params->n_agencies; i++) {
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
cpWalk(CustomPayload* this, State* params, WalkOptions* walkoptions) {
	State* s = this->methods->walk(this->soul, params, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}
State*
cpWalkBack(CustomPayload* this, State* params, WalkOptions* walkoptions) {
	State* s = this->methods->walkBack(this->soul, params, walkoptions);
	s->prev_edge = (EdgePayload*)this;
	return s;
}

#undef ROUTE_REVERSE
#include "edgeweights.c"
#define ROUTE_REVERSE
#include "edgeweights.c"
#undef ROUTE_REVERSE
