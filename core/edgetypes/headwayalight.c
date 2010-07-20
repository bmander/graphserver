#include "../graphserver.h"

// HEADWAYALIGHT FUNCTIONS

HeadwayAlight*
haNew(  ServiceId service_id, ServiceCalendar* calendar, Timezone* timezone, int agency, char* trip_id, int start_time, int end_time, int headway_secs ) {
  HeadwayAlight* ret = (HeadwayAlight*)malloc(sizeof(HeadwayAlight));
  ret->external_id = 0;
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
haWalk(EdgePayload* this, State* state, WalkOptions* options) {
    State* ret = stateDup( state );
    ret->trip_id = NULL;
    
    return ret;
}

inline State*
haWalkBack( EdgePayload* superthis, State* state, WalkOptions* options ) {
    HeadwayAlight* this = (HeadwayAlight*)superthis;
    
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
    
    if (time_since_midnight < this->start_time ) {
        return NULL;
    }
    
    // Dupe state and advance time by the waiting time
    State* ret = stateDup( state );
    
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
    for(i=0; i<state->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
    
    return ret;
    
}
