#define ABSOLUTE_MAX_WALK 1000000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
#define SECS_IN_DAY 86400

#ifndef ROUTE_REVERSE
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           += delta_t; \
  for(i=0; i<params->n_agencies; i++) { \
      ServicePeriod* sp = params->service_periods[i]; \
      if(sp && ret->time >= sp->end_time) { \
        ret->service_periods[i] = sp->next_period; \
      } \
  }
#else
#define ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t) \
  int i; \
  ret->time           -= delta_t; \
  for(i=0; i<params->n_agencies; i++) { \
    ServicePeriod* sp = params->service_periods[i]; \
    if(sp && ret->time < sp->begin_time) { \
      ret->service_periods[i] = sp->prev_period; \
    } \
  }
#endif


inline State*
#ifndef ROUTE_REVERSE
linkWalk(EdgePayload* this, State* params, WalkOptions* options) {
#else
linkWalkBack(EdgePayload* this, State* params, WalkOptions* options) {
#endif
    
  State* ret = stateDup( params );

  ret->prev_edge = this;

  return ret;
}

inline State*
#ifndef ROUTE_REVERSE
elapseTimeWalk(EdgePayload* this, State* params, WalkOptions* options) {
#else
elapseTimeWalkBack(EdgePayload* this, State* params, WalkOptions* options) {
#endif
  
  State* ret = stateDup( params );
  
  int delta_t = ((ElapseTime*)this)->seconds;
  
  ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t);

  // this could have a multiplier via WalkOptions, but this is currently not necessary
  ret->weight += delta_t;
  ret->prev_edge = this;

  return ret;
}


#ifndef ROUTE_REVERSE
inline State*
waitWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( params );
    
    ret->prev_edge = superthis;
    
    long secs_since_local_midnight = (params->time+tzUtcOffset(this->timezone, params->time))%SECS_IN_DAY;
    long wait_time = this->end - secs_since_local_midnight;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time += wait_time;
    ret->weight += wait_time;
    
    return ret;
}
#else
inline State*
waitWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( params );
    
    ret->prev_edge = superthis;
    
    long secs_since_local_midnight = (params->time+tzUtcOffset(this->timezone, params->time))%SECS_IN_DAY;
    long wait_time = secs_since_local_midnight - this->end;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time -= wait_time;
    ret->weight += wait_time;
    
    return ret;
}
#endif

inline State*
#ifndef ROUTE_REVERSE
streetWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
#else
streetWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
#endif
  Street* this = (Street*)superthis;
  State* ret = stateDup( params );

  // Elevation considerations
  long t_horiz = (long)(this->length/options->walking_speed);
#ifndef ROUTE_REVERSE
  long t_up = (long)(this->rise/(options->walking_speed*options->uphill_slowness));
  long t_down = (long)(this->fall*options->downhill_fastness);
#else
  long t_up = (long)(this->fall/(options->walking_speed*options->uphill_slowness));
  long t_down = (long)(this->rise*options->downhill_fastness);
#endif
    
  long delta_t = t_horiz + t_up - t_down;
  if( delta_t < 0 ) {
      delta_t = 0;
  }
    
  long delta_w = t_horiz*options->walking_reluctance + t_up*options->hill_reluctance - t_down;
  if( delta_w < 0 ) {
      delta_w = 0;
  }

  // max_walk overage considerations
  double end_dist = params->dist_walked + this->length;
  if(end_dist > options->max_walk)
    delta_w += (end_dist - options->max_walk)*options->walking_overage*delta_t;
  
  // turning considerations
  if( params->prev_edge &&
      params->prev_edge->type == PL_STREET &&
      ((Street*)params->prev_edge)->way != this->way ) {
    delta_w += options->turn_penalty;
  }

  ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t);

  if (end_dist > ABSOLUTE_MAX_WALK) //TODO profile this to see if it's worth it
    ret->weight = MAX_LONG;
  else
    ret->weight       += this->slog*delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge = superthis;

  return ret;
}

inline State*
#ifndef ROUTE_REVERSE
egressWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
#else
egressWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
#endif
  Egress* this = (Egress*)superthis;
  State* ret = stateDup( params );

  double end_dist = params->dist_walked + this->length;
  // no matter what the options say (e.g. you're on a bike), 
  // the walking speed should be 1.1 mps, because you can't ride in
  // a station
  long delta_t = (long)(this->length/1.1);
  long delta_w = delta_t*options->walking_reluctance;
  if(end_dist > options->max_walk)
    delta_w += (end_dist - options->max_walk)*options->walking_overage*delta_t;

  ELAPSE_TIME_AND_SERVICE_PERIOD(ret, delta_t);

  ret->weight        += delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge = superthis;

  return ret;
}

inline State*
#ifndef ROUTE_REVERSE
headwayWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
#else
headwayWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
#endif
    Headway* this = (Headway*)superthis;
    
    // if the params->service_period is NULL, use the params->time to find the service_period
    // the service_period is actually a denormalization of the params->time
    // this way, the user doesn't need to worry about it
    
    ServicePeriod* service_period = params->service_periods[this->agency];
    if( !service_period )
#ifndef ROUTE_REVERSE
        service_period = scPeriodOfOrAfter( this->calendar, params->time );
#else
        service_period = scPeriodOfOrBefore( this->calendar, params->time );
#endif
    params->service_periods[this->agency] = service_period;
    
    // if the schedule never runs
    // or if the schedule does not run on this day
    // this link goes nowhere
    if( !service_period ||
        !spPeriodHasServiceId( service_period, this->service_id) ) {
      return NULL;
    }
    
    State* ret = stateDup( params );
    
    long adjusted_time = spNormalizeTime( service_period, tzUtcOffset(this->timezone, params->time), params->time );
  
    long transfer_penalty=0;
    //if this is a transfer
    if( !params->prev_edge ||
        params->prev_edge->type != PL_HEADWAY  ||    //the last edge wasn't a bus
        !((Headway*)params->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
        strcmp( ((Headway*)params->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same

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
    } else if( !params->prev_edge ||
        !params->prev_edge->type == PL_HEADWAY  ||    //the last edge wasn't a bus
        !((Headway*)params->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
        strcmp( ((Headway*)params->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
        wait = this->wait_period;
    }
    
    ret->time   += wait + this->transit;
    ret->weight += wait + this->transit + transfer_penalty;
    
    for(i=0; i<params->n_agencies; i++) {
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
    } else if( !params->prev_edge ||
        !params->prev_edge->type == PL_HEADWAY  ||    //the last edge wasn't a bus
        !((Headway*)params->prev_edge)->trip_id               ||    //it was a bus, but the trip_id was NULL
        strcmp( ((Headway*)params->prev_edge)->trip_id, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
        wait = this->wait_period;
    }
    
    ret->time   -= wait + this->transit;
    ret->weight += wait + this->transit + transfer_penalty;
    
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
          ret->service_periods[i] = ret->service_periods[i]->prev_period;
        }
    }
#endif
    ret->dist_walked    = 0;
    ret->prev_edge = superthis;

    return ret;
}
