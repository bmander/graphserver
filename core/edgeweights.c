#define WALKING_SPEED 0.85    //meters per second
#define MIN_TRANSFER_TIME 300 //five minutes
#define TRANSFER_PENALTY 3    //rough measure of how bad a close transfer is
#define MAX_WALK 1200         //in meters; he better part of a mile
#define WALKING_OVERAGE 0.1   //hassle/second/meter
#define WALKING_RELUCTANCE 2  //hassle/second
#define ABSOLUTE_MAX_WALK 100000 //meters. 100 km. prevents overflow
#define MAX_LONG 2147483647
/*#define WALKING_SPEED 0.85    //meters per second
#define MIN_TRANSFER_TIME 0 //five minutes
#define TRANSFER_PENALTY 0    //rough measure of how bad a close transfer is
#define MAX_WALK 100000         //in meters; very large
#define WALKING_OVERAGE 0     //hassle/second/meter
#define WALKING_RELUCTANCE 1  //hassle/second*/

inline State*
#ifndef ROUTE_REVERSE
linkWalk(Link* this, State* params) {
#else
linkWalkBack(Link* this, State* params) {
#endif
  State* ret = stateDup( params );

  ret->prev_edge_type = PL_LINK;
  ret->prev_edge_name = this->name;

  return ret;
}

inline State*
#ifndef ROUTE_REVERSE
streetWalk(Street* this, State* params) {
#else
streetWalkBack(Street* this, State* params) {
#endif
  State* ret = stateDup( params );

  double end_dist = params->dist_walked + this->length;
  long delta_t = (long)(this->length/WALKING_SPEED);
  long delta_w = delta_t*WALKING_RELUCTANCE;
  if(end_dist > MAX_WALK)
    delta_w += (end_dist - MAX_WALK)*WALKING_OVERAGE*delta_t;

#ifndef ROUTE_REVERSE
  ret->time           += delta_t;
  if(params->calendar_day && ret->time >= params->calendar_day->end_time) {
    ret->calendar_day = params->calendar_day->next_day;
  }
#else
  ret->time           -= delta_t;
  if(params->calendar_day && ret->time < params->calendar_day->begin_time) {
    ret->calendar_day = params->calendar_day->prev_day;
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

inline State*
#ifndef ROUTE_REVERSE
thsWalk(TripHopSchedule* this, State* params) {
#else
thsWalkBack(TripHopSchedule* this, State* params) {
#endif
    
    TripHop* th;
#ifndef ROUTE_REVERSE
    th = thsCollapse(this, params);
#else
    th = thsCollapseBack(this, params);
#endif
    
    State* ret;
#ifndef ROUTE_REVERSE
    ret = triphopWalk(th, params);
#else
    ret = triphopWalkBack(th, params);
#endif
    
    return ret;
}

inline State*
#ifndef ROUTE_REVERSE
triphopWalk(TripHop* this, State* params) {
#else
triphopWalkBack(TripHop* this, State* params) {
#endif
    State* ret = stateDup( params );

    long adjusted_time = thsSecondsSinceMidnight( this->schedule, params );

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
      if( wait < MIN_TRANSFER_TIME && 
          params->num_transfers > 0)
        transfer_penalty = (MIN_TRANSFER_TIME-wait)*TRANSFER_PENALTY;
      //transfer_penalty = 1000; //penalty of making a transfer; flat rate.

      ret->num_transfers += 1;
    }

#ifndef ROUTE_REVRSE
    ret->time           += wait + this->transit;
    if( ret->time >= ret->calendar_day->end_time) {
      ret->calendar_day = ret->calendar_day->next_day;
    }
#else
    ret->time           -= wait - this->transit;
    if( ret->time < ret->calendar_day->begin_time) {
      ret->calendar_day = ret->calendar_day->prev_day;
    }
#endif
    ret->weight         += wait + this->transit + transfer_penalty;
    ret->dist_walked    = 0;
    ret->prev_edge_type = PL_TRIPHOP;
    ret->prev_edge_name = this->trip_id;

    return ret;
}

// Note that this has the side effect of filling in the params->calendar_day if it is not already set
inline TripHop*
#ifndef ROUTE_REVERSE
thsCollapse(TripHopSchedule* this, State* params) {
#else
thsCollapseBack(TripHopSchedule* this, State* params) {
#endif

    // if the params->calendar_day is NULL, use the params->time to find the calendar_day
    // the calendar_day is actually a denormalization of the params->time
    // this way, the user doesn't need to worry about it
    CalendarDay* calendar_day = params->calendar_day;
    if( !calendar_day )
#ifndef ROUTE_REVERSE
      calendar_day = calDayOfOrAfter( this->calendar, params->time );
#else
      calendar_day = calDayOfOrBefore( this->calendar, params->time );
#endif
    params->calendar_day = calendar_day;

    // if the schedule never runs
    // or if the schedule does not run on this day
    // this link goes nowhere
    if( !calendar_day ||
        !calDayHasServiceId( calendar_day, this->service_id) ||
        this->n == 0 ) {
      return NULL;
    }

    long adjusted_time = thsSecondsSinceMidnight( this, params );

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

    TripHop* inquestion = &(this->hops[mid]);

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
    return &(this->hops[high]);
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
    return &(this->hops[low]);
#endif
}
