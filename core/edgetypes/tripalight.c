#include "../graphserver.h"
#include <stdio.h>

// ALIGHT FUNCTIONS

TripAlight*
alNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  TripAlight* ret = (TripAlight*)malloc(sizeof(TripAlight));
  ret->external_id = 0;
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
alDestroy(TripAlight* this) {
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
alGetCalendar( TripAlight* this ) {
  return this->calendar;
}

Timezone*
alGetTimezone( TripAlight* this ) {
  return this->timezone;
}

int
alGetAgency( TripAlight* this ) {
  return this->agency;
}

ServiceId
alGetServiceId( TripAlight* this ) {
  return this->service_id;
}

int
alGetNumAlightings( TripAlight* this) {
  return this->n;
}

void
alAddAlighting(TripAlight* this, char* trip_id, int arrival, int stop_sequence) {
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
alGetAlightingTripId(TripAlight* this, int i) {
    if(i<0 || i >= this->n) {
        return NULL;
    }
    
    return this->trip_ids[i];
}

int
alGetAlightingArrival(TripAlight* this, int i) {
    if(i<0 || i >= this->n) {
        return -1;
    }
    
    return this->arrivals[i];
}

int
alGetAlightingStopSequence(TripAlight* this, int i) {
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
alSearchAlightingsList(TripAlight* this, int time) {
    return binsearch( this->arrivals, this->n, time, 0);
}

int
alGetLastAlightingIndex(TripAlight* this, int time) {
    //if insertion point is before end of array, -1 will be returned, which is coincidentally the error code
    return binsearch( this->arrivals, this->n, time, 1 );
}

int
alGetOverage(TripAlight* this) {
    return this->overage;
}

int
alGetAlightingIndexByTripId(TripAlight* this, char* trip_id) {
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
    TripAlight* this = (TripAlight*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period ) {
        service_period = scPeriodOfOrBefore( this->calendar, state->time );
        state->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, state->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    }
    
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
    
    // if no alighting was found for the present day, but the alighting ran yesterday, check yesterday
    if( last_alighting_index == -1 && 
        service_period->prev_period &&
        spPeriodHasServiceId( service_period->prev_period, this->service_id ) ) {
        time_since_midnight += SECS_IN_DAY;
	last_alighting_index = alGetLastAlightingIndex( this, time_since_midnight );
    }

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
