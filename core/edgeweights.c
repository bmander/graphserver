#define ABSOLUTE_MAX_WALK 1000000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
#define SECS_IN_DAY 86400

#ifndef ROUTE_REVERSE
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           += delta_t; \
  for(i=0; i<state->n_agencies; i++) { \
      ServicePeriod* sp = state->service_periods[i]; \
      if(sp && ret->time >= sp->end_time) { \
        ret->service_periods[i] = sp->next_period; \
      } \
  }
#else
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           -= delta_t; \
  for(i=0; i<state->n_agencies; i++) { \
    ServicePeriod* sp = state->service_periods[i]; \
    if(sp && ret->time < sp->begin_time) { \
      ret->service_periods[i] = sp->prev_period; \
    } \
  }
#endif

inline State*
#ifndef ROUTE_REVERSE
headwayWalk(EdgePayload* superthis, State* state, WalkOptions* options) {
#else
headwayWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
#endif
    Headway* this = (Headway*)superthis;
    
    // if the state->service_period is NULL, use the state->time to find the service_period
    // the service_period is actually a denormalization of the state->time
    // this way, the user doesn't need to worry about it
    
    ServicePeriod* service_period = state->service_periods[this->agency];
    if( !service_period )
#ifndef ROUTE_REVERSE
        service_period = scPeriodOfOrAfter( this->calendar, state->time );
#else
        service_period = scPeriodOfOrBefore( this->calendar, state->time );
#endif
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
#ifndef ROUTE_REVERSE
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
#else
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
#endif
    ret->dist_walked    = 0;
    ret->prev_edge = superthis;

    return ret;
}
