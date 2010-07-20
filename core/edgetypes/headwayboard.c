#include "../graphserver.h"

// HEADWAYBOARD FUNCTIONS

HeadwayBoard*
hbNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs ) {
  HeadwayBoard* ret = (HeadwayBoard*)malloc(sizeof(HeadwayBoard));
  ret->external_id = 0;
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
hbWalk( EdgePayload* superthis, State* state, WalkOptions* options ) {
    HeadwayBoard* this = (HeadwayBoard*)superthis;
    
    //Get service period cached in travel state. If it doesn't exist, figure it out and cache it
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period )
        service_period = scPeriodOfOrAfter( this->calendar, state->time );
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
    State* ret = stateDup( state );
    
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
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}

inline State*
hbWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
    HeadwayBoard* this = (HeadwayBoard*)superthis;
    
    State* ret = stateDup( state );
    
    int wait = this->headway_secs; 
    ret->time   -= wait;
    ret->weight += wait; //transfer penalty
    ret->trip_id = NULL;
    
    return ret;
}
