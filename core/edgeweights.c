#define MIN_TRANSFER_TIME 1//300 //five minutes
#define TRANSFER_PENALTY 3    //rough measure of how bad a close transfer is
//#define MAX_WALK 1200         //in meters; he better part of a mile
#define MAX_WALK 10000
#define WALKING_OVERAGE 0.1   //hassle/second/meter
//#define WALKING_RELUCTANCE 2  //hassle/second
#define WALKING_RELUCTANCE 1
#define ABSOLUTE_MAX_WALK 100000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
#define WAITING_RELUCTANCE 1
#define SECS_IN_DAY 86400
/*#define MIN_TRANSFER_TIME 0 //five minutes
#define TRANSFER_PENALTY 0    //rough measure of how bad a close transfer is
#define MAX_WALK 100000         //in meters; very large
#define WALKING_OVERAGE 0     //hassle/second/meter
#define WALKING_RELUCTANCE 1  //hassle/second*/

inline State*
#ifndef ROUTE_REVERSE
linkWalk(EdgePayload* this, State* params, WalkOptions* options) {
#else
linkWalkBack(EdgePayload* this, State* params, WalkOptions* options) {
#endif
    
  State* ret = stateDup( params );

  ret->prev_edge_type = PL_LINK;
  ret->prev_edge_name = ((Link*)this)->name;

  return ret;
}

#ifndef ROUTE_REVERSE
inline State*
waitWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( params );
    
    ret->prev_edge_type = PL_WAIT;
    
    long secs_since_local_midnight = (params->time+tzUtcOffset(this->timezone, params->time))%SECS_IN_DAY;
    long wait_time = this->end - secs_since_local_midnight;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time += wait_time;
    ret->weight += wait_time*WAITING_RELUCTANCE;
    
    if(params->prev_edge_type==PL_TRIPHOP) {
        ret->weight += options->transfer_penalty;
    }
    
    return ret;
}
#else
inline State*
waitWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
    Wait* this = (Wait*)superthis;
    
    State* ret = stateDup( params );
    
    ret->prev_edge_type = PL_WAIT;
    
    long secs_since_local_midnight = (params->time+tzUtcOffset(this->timezone, params->time))%SECS_IN_DAY;
    long wait_time = secs_since_local_midnight - this->end;
    if(wait_time<0) {
        wait_time += SECS_IN_DAY;
    }
    
    ret->time -= wait_time;
    ret->weight += wait_time*WAITING_RELUCTANCE;
    
    if(params->prev_edge_type==PL_TRIPHOP) {
        ret->weight += options->transfer_penalty;
    }
    
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

  double end_dist = params->dist_walked + this->length;
  long delta_t = (long)(this->length/options->walking_speed);
  long delta_w = delta_t*WALKING_RELUCTANCE;
  if(end_dist > MAX_WALK)
    delta_w += (end_dist - MAX_WALK)*WALKING_OVERAGE*delta_t;

  int i;
#ifndef ROUTE_REVERSE
  ret->time           += delta_t;
  for(i=0; i<params->n_agencies; i++) {
      ServicePeriod* sp = params->service_periods[i];
      if(sp && ret->time >= sp->end_time) {
        ret->service_periods[i] = sp->next_period;
      }
  }
#else
  ret->time           -= delta_t;
  for(i=0; i<params->n_agencies; i++) {
    ServicePeriod* sp = params->service_periods[i];
    if(sp && ret->time < sp->begin_time) {
      ret->service_periods[i] = sp->prev_period;
    }
  }
#endif
  if (end_dist > ABSOLUTE_MAX_WALK) //TODO profile this to see if it's worth it
    ret->weight = MAX_LONG;
  else
    ret->weight       += delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge_type = PL_STREET;
  ret->prev_edge_name = this->name;

  return ret;
}

// This function is never called by the router - it's mostly a convenience method to be wrapped
// by a higher-level langauge for the purpose of debugging.
inline State*
#ifndef ROUTE_REVERSE
thsWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
#else
thsWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
#endif
    TripHopSchedule* this = (TripHopSchedule*)superthis;
    
    TripHop* th;
#ifndef ROUTE_REVERSE
    th = thsCollapse(this, params);
#else
    th = thsCollapseBack(this, params);
#endif
    
    if(!th)
        return NULL;
    
    State* ret;
#ifndef ROUTE_REVERSE
    ret = th->walk((EdgePayload*)th, params, options);
#else
    ret = th->walkBack((EdgePayload*)th, params, options);
#endif
    
    return ret;
}

inline State*
#ifndef ROUTE_REVERSE
triphopWalk(EdgePayload* superthis, State* params, WalkOptions* options) {
#else
triphopWalkBack(EdgePayload* superthis, State* params, WalkOptions* options) {
#endif
    
    TripHop* this = (TripHop*)superthis;
    
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
    
    long wait;
#ifndef ROUTE_REVERSE
    wait = (this->depart - adjusted_time);
#else
    wait = (adjusted_time - this->arrive);
#endif
  
    long transfer_penalty=0;
    //if this is a transfer
    if( params->prev_edge_type != PL_TRIPHOP  ||    //the last edge wasn't a bus
        !params->prev_edge_name               ||    //it was a bus, but the trip_id was NULL
        strcmp( params->prev_edge_name, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same

      //add a weight penalty to the transfer under some conditions
      //if( wait < MIN_TRANSFER_TIME && 
      //    params->num_transfers > 0) {
      //  transfer_penalty = (MIN_TRANSFER_TIME-wait)*TRANSFER_PENALTY;
      //}
      transfer_penalty = options->transfer_penalty; //penalty of making a transfer; flat rate. "all things being equal, transferring costs a little"

      ret->num_transfers += 1;
    }

    int i;
#ifndef ROUTE_REVERSE
    ret->time           += wait + this->transit;
    if(adjusted_time>this->depart) {
        stateDestroy( ret );
        return NULL;
    } else {
        ret->weight += wait + this->transit + transfer_penalty;
    }
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time >= ret->service_periods[i]->end_time) {
          ret->service_periods[i] = ret->service_periods[i]->next_period;
        }
    }
#else
    ret->time           -= (wait + this->transit);
    if(adjusted_time<this->arrive) {
        stateDestroy( ret );
        return NULL;
    } else {
        ret->weight += wait + this->transit + transfer_penalty;
    }
    for(i=0; i<params->n_agencies; i++) {
        if( ret->service_periods[i] && ret->time < ret->service_periods[i]->begin_time) {
          ret->service_periods[i] = ret->service_periods[i]->prev_period;
        }
    }
#endif
    ret->dist_walked    = 0;
    ret->prev_edge_type = PL_TRIPHOP;
    ret->prev_edge_name = this->trip_id;
    
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
    if( params->prev_edge_type != PL_HEADWAY  ||    //the last edge wasn't a bus
        !params->prev_edge_name               ||    //it was a bus, but the trip_id was NULL
        strcmp( params->prev_edge_name, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same

      //add a weight penalty to the transfer under some conditions
      //if( wait < MIN_TRANSFER_TIME && 
      //    params->num_transfers > 0) {
      //  transfer_penalty = (MIN_TRANSFER_TIME-wait)*TRANSFER_PENALTY;
      //}
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
    } else if( !(params->prev_edge_type == PL_HEADWAY || params->prev_edge_type == PL_HEADWAY)  ||    //the last edge wasn't a bus
        !params->prev_edge_name               ||    //it was a bus, but the trip_id was NULL
        strcmp( params->prev_edge_name, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
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
    } else if( !(params->prev_edge_type == PL_HEADWAY || params->prev_edge_type == PL_HEADWAY)  ||    //the last edge wasn't a bus
        !params->prev_edge_name               ||    //it was a bus, but the trip_id was NULL
        strcmp( params->prev_edge_name, this->trip_id ) != 0 )  { //the current and previous trip_ids are not the same
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
    ret->prev_edge_type = PL_HEADWAY;
    ret->prev_edge_name = this->trip_id;

    return ret;
}

// Note that this has the side effect of filling in the params->service_period if it is not already set
inline TripHop*
#ifndef ROUTE_REVERSE
thsCollapse(TripHopSchedule* this, State* params) {
#else
thsCollapseBack(TripHopSchedule* this, State* params) {
#endif

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
    
    long adjusted_time = spNormalizeTime( service_period, tzUtcOffset(this->timezone, params->time), params->time );
    
#ifndef ROUTE_REVERSE
    return thsGetNextHop(this, adjusted_time);
#else
    return thsGetLastHop(this, adjusted_time);
#endif

}

#ifndef ROUTE_REVERSE
inline TripHop* thsGetNextHop(TripHopSchedule* this, long time) {
#else
inline TripHop* thsGetLastHop(TripHopSchedule* this, long time) {
#endif
  int low = -1;
  int high = this->n;
  int mid = 0;   //initialize cursor to make compiler happy

  if(high == 0)    //bail if there are no departures
    return NULL;

  while( low != high-1 ) {
#ifndef ROUTE_REVERSE
    mid = (low+high)/2;
#else
    mid = ceil( (low+high)/2.0 );
#endif

    TripHop* inquestion = this->hops[mid];

#ifndef ROUTE_REVERSE
    if( time < inquestion->depart ) {
      high = mid;
    } else if( time > inquestion->depart ){
      low = mid;
    } else {  //time == the departure at the cursor
      return inquestion;
    }
  }
  
  if( high == this->n ) //there is no next departure
    return NULL;
  else
    return this->hops[high];
#else
    if( time < inquestion->arrive ) {
      high = mid;
    } else if( time > inquestion->arrive ){
      low = mid;
    } else {  //time == the arrival at the cursor
      return inquestion;
    }
  }
  
  if( low == -1 ) //thee is no previous arrival
    return NULL;
  else
    return this->hops[low];
#endif
}
