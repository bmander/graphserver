#define WALKING_SPEED 0.85    //meters per second
#define MAX_WALK 1200         //in meters; he better part of a mile
#define WALKING_OVERAGE 0.1   //hassle/second/meter
#define WALKING_RELUCTANCE 2  //hassle/second

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
  ret->weight         += delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge_type = PL_STREET;
  ret->prev_edge_name = this->name;

  return ret;
}
