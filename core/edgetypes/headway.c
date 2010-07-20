#include "../graphserver.h"

//HEADWAY FUNCTIONS

Headway*
headwayNew(int begin_time, int end_time, int wait_period, int transit, char* trip_id, ServiceCalendar* calendar, Timezone* timezone, int agency, ServiceId service_id) {
    Headway* ret = (Headway*)malloc(sizeof(Headway));
    
    ret->external_id = 0;
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


inline State*
headwayWalkGeneral(EdgePayload* superthis, State* state, WalkOptions* options, int forward) {
    Headway* this = (Headway*)superthis;
    
    // if the state->service_period is NULL, use the state->time to find the service_period
    // the service_period is actually a denormalization of the state->time
    // this way, the user doesn't need to worry about it
    
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period ) {
        if( forward ) {
            service_period = scPeriodOfOrAfter( this->calendar, state->time );
        } else {
            service_period = scPeriodOfOrBefore( this->calendar, state->time );
        }
    }

    state->service_periods[this->agency] = service_period;
    
    // if the schedule never runs
    // or if the schedule does not run on this day
    // this link goes nowhere
    if( !service_period ||
        !spPeriodHasServiceId( service_period, this->service_id) ) {
      return NULL;
    }
    
    State* ret = stateDup( state );
    
    long adjusted_time = spNormalizeTime( service_period, tzUtcOffset(this->timezone, state->time), state->time );
  
    long transfer_penalty=0;
    //if this is a transfer
    if( !state->prev_edge ||
        state->prev_edge->type != PL_HEADWAY  ||    //the last edge wasn't a bus
        !((Headway*)state->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
        strcmp( ((Headway*)state->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same

      transfer_penalty = options->transfer_penalty; //penalty of making a transfer; flat rate. "all things being equal, transferring costs a little"

      ret->num_transfers += 1;
    }

    int i;
    long wait=0;
    if( forward ) {
        if( adjusted_time > this->end_time ) {
            stateDestroy( ret );
            return NULL;
        }
        
        if( adjusted_time <= this->begin_time ) {
            wait = this->begin_time - adjusted_time;
        } else if( !state->prev_edge ||
            !state->prev_edge->type == PL_HEADWAY  ||    //the last edge wasn't a bus
            !((Headway*)state->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
            strcmp( ((Headway*)state->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
            wait = this->wait_period;
        }
        
        ret->time   += wait + this->transit;
        ret->weight += wait + this->transit + transfer_penalty;
        
        for(i=0; i<state->n_agencies; i++) {
            if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
              ret->service_periods[i] = ret->service_periods[i]->next_period;
            }
        }
    } else {
        if( adjusted_time < this->begin_time ) {
            stateDestroy( ret );
            return NULL;
        }
        
        if( adjusted_time >= this->end_time ) {
            wait = adjusted_time - this->begin_time;
        } else if( !state->prev_edge ||
            !state->prev_edge->type == PL_HEADWAY  ||    //the last edge wasn't a bus
            !((Headway*)state->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
            strcmp( ((Headway*)state->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
            wait = this->wait_period;
        }
        
        ret->time   -= wait + this->transit;
        ret->weight += wait + this->transit + transfer_penalty;
        
        for(i=0; i<state->n_agencies; i++) {
            if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
              ret->service_periods[i] = ret->service_periods[i]->prev_period;
            }
        }
    }

    ret->dist_walked    = 0;
    ret->prev_edge = superthis;

    return ret;
}


inline State*
headwayWalk(EdgePayload* superthis, State* state, WalkOptions* options) {
    return headwayWalkGeneral( superthis, state, options, TRUE );
}


inline State*
headwayWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
    return headwayWalkGeneral( superthis, state, options, FALSE );
}
