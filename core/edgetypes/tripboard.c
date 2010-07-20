
#include "../graphserver.h"

//TRIPBOARD FUNCTIONS

TripBoard*
tbNew( ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency ) {
  TripBoard* ret = (TripBoard*)malloc(sizeof(TripBoard));
  ret->external_id = 0;
  ret->type = PL_TRIPBOARD;
  ret->n = 0;
  ret->departs = NULL;
  ret->trip_ids = NULL;
  ret->stop_sequences = NULL;
    
  ret->calendar = calendar;
  ret->timezone = timezone;
  ret->agency = agency;
  ret->service_id = service_id;
    
  ret->walk = &tbWalk;
  ret->walkBack = &tbWalkBack;
    
  ret->overage = NO_OVERAGE_VALUE;
    
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
  if(this->stop_sequences){
    free(this->stop_sequences);
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
tbAddBoarding(TripBoard* this, char* trip_id, int depart, int stop_sequence) {
    if (depart > SECS_IN_DAY+this->overage)
        this->overage = depart-SECS_IN_DAY;
    
    // init the trip_id, depart list
    if(this->n==0) {
        this->departs = (int*)malloc(sizeof(int));
        this->trip_ids = (char**)malloc(sizeof(char*));
        this->stop_sequences = (int*)malloc(sizeof(int));
        
        this->departs[0] = depart;
        this->stop_sequences[0] = stop_sequence;
        
        int n = strlen(trip_id)+1;
        this->trip_ids[0] = (char*)malloc(sizeof(char)*(n));
        memcpy(this->trip_ids[0], trip_id, n);
        
    } else {
        //allocate new, expanded lists with size enough for the extra departure
        int* next_departs = (int*)malloc((this->n+1)*sizeof(int));
        char** next_trip_ids = (char**)malloc((this->n+1)*sizeof(char*));
        int* next_stop_sequences = (int*)malloc((this->n+1)*sizeof(int));
        
        //find insertion point
        int m = tbSearchBoardingsList(this, depart);
        
        //copy old list to new list up to insertion point
        int i;
        for(i=0; i<m; i++) {
            next_departs[i] = this->departs[i];
            next_trip_ids[i] = this->trip_ids[i];
            next_stop_sequences[i] = this->stop_sequences[i];
        }
        
        //copy new departure into lists
        next_departs[m] = depart;
        int strn = strlen(trip_id)+1;
        next_trip_ids[m] = (char*)malloc(sizeof(char)*(strn));
        memcpy(next_trip_ids[m], trip_id, strn);
        next_stop_sequences[m] = stop_sequence;
        
        //copy old list to new list from insertion point on
        for(i=m; i<this->n; i++) {
            next_departs[i+1] = this->departs[i];
            next_trip_ids[i+1] = this->trip_ids[i];
            next_stop_sequences[i+1] = this->stop_sequences[i];
        }
        
        //free and replace old lists
        free(this->departs);
        free(this->trip_ids);
        free(this->stop_sequences);
        this->departs = next_departs;
        this->trip_ids = next_trip_ids;
        this->stop_sequences = next_stop_sequences;
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
tbGetBoardingStopSequence(TripBoard* this, int i) {
    if(i<0 || i >= this->n) {
        return -1;
    }
    
    return this->stop_sequences[i];
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

int
tbGetBoardingIndexByTripId(TripBoard* this, char* trip_id) {
    /* returns the boarding index of the boarding with the given trip_id */
    
    int i;
    for(i=0; i<this->n; i++) {
        if( strcmp(this->trip_ids[i], trip_id)==0 ) {
            return i;
        }
    }
    
    return -1;
    
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
tbWalk( EdgePayload* superthis, State* state, WalkOptions* options ) {
    TripBoard* this = (TripBoard*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period ) {
        service_period = scPeriodOfOrAfter( this->calendar, state->time );
        state->service_periods[this->agency] = service_period;
    
        //If still can't find service_period, state->time is beyond service calendar, so bail
        if( !service_period )
            return NULL;
    }
    
    long time_since_midnight = tzTimeSinceMidnight( this->timezone, state->time );
        
    
    /* if the schedules's service ID (say, WKDY) runs yesterday with respect to
     * the state's current service period (say, the state is currently on a
     * wednesday, the WKDY schedule does run yesterday) and the state's current 
     * time since midnight (say, 1 AM, 60 minutes since midnight) is less than 
     * the amount by which the schedule pokes out over midnight (say that the
     * schedule runs into 2 AM), then increment the time_since_midnight by a day
     * and proceed, such that we will discover that the next arrival comes some
     * time in the next 60 minutes
     */
    if( this->overage != NO_OVERAGE_VALUE &&
        this->overage >= time_since_midnight &&
        service_period->prev_period &&
        spPeriodHasServiceId( service_period->prev_period, this->service_id )) {
            
        time_since_midnight += SECS_IN_DAY;
            
    /* if none of that is true *and* the schedule doesn't run on the current
     * day, then this schedule contains no departures that leave any time soon
     */
    } else if( !spPeriodHasServiceId( service_period, this->service_id ) ) {
        return NULL;
    }
    
    int next_boarding_index = tbGetNextBoardingIndex( this, time_since_midnight );
    
    if( next_boarding_index == -1 ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    ret->stop_sequence = this->stop_sequences[next_boarding_index];
    
    ret->num_transfers += 1;
    
    int next_boarding_time = this->departs[next_boarding_index];
    int wait = (next_boarding_time - time_since_midnight);
    
    ret->time   += wait;
    ret->weight += wait + 1; //base transfer penalty
    ret->weight += options->transfer_penalty;
    
    ret->trip_id = this->trip_ids[next_boarding_index];
    
    // Make sure the service period caches are updated if we've traveled over a service period boundary
    int i;
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

inline State*
tbWalkBack(EdgePayload* this, State* state, WalkOptions* options) {
    State* ret = stateDup( state );
    ret->trip_id = NULL;
    
    return ret;
}
