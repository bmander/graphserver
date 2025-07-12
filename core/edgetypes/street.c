#include "../graphserver.h"

//STREET FUNCTIONS
Street*
streetNew(const char *name, double length, int reverse_of_source) {
  Street* ret = (Street*)malloc(sizeof(Street));
  ret->external_id = 0;
  ret->type = PL_STREET;
  ret->name = (char*)malloc((strlen(name)+1)*sizeof(char));
  strcpy(ret->name, name);
  ret->length = length;
  ret->rise = 0;
  ret->fall = 0;
  ret->slog = 1;
  ret->way = 0;
  ret->reverse_of_source = reverse_of_source;
    
  //bind functions to methods
  ret->walk = &streetWalk;
  ret->walkBack = &streetWalkBack;

  return ret;
}

Street*
streetNewElev(const char *name, double length, float rise, float fall, int reverse_of_source) {
    Street* ret = streetNew( name, length, reverse_of_source );
    ret->rise = rise;
    ret->fall = fall;
    return ret;
}

void
streetDestroy(Street* tokill) {
  free(tokill->name);
  free(tokill);
}

char*
streetGetName(Street* this) {
    return this->name;
}

double
streetGetLength(Street* this) {
    return this->length;
}

float
streetGetRise(Street* this) {
    return this->rise;
}

void
streetSetRise(Street* this, float rise) {
    this->rise = rise;
}

float
streetGetFall(Street* this) {
    return this->fall;
}

void
streetSetFall(Street* this, float fall) {
    this->fall = fall;
}

float
streetGetSlog(Street* this) {
    return this->slog;
}

void
streetSetSlog(Street* this, float slog) {
    this->slog = slog;
}

long
streetGetWay(Street* this) {
    return this->way;   
}

void
streetSetWay(Street* this, long way) {
    this->way = way;
}

int
streetGetReverseOfSource( Street *this ) {
    return this->reverse_of_source;
}

#ifndef EDGEWEIGHTS_FIRSTTHROUGH
#define EDGEWEIGHTS_FIRSTTHROUGH 1
float speed_from_grade(WalkOptions* options, float grade) {
  if( grade <= 0 ) {
      return options->downhill_fastness*grade + options->walking_speed;
  } else if( grade <= options->phase_change_grade ) {
      return options->phase_change_velocity_factor*grade*grade + options->downhill_fastness*grade + options->walking_speed;
  } else {
      return (options->uphill_slowness*options->walking_speed)/(options->uphill_slowness+grade);
  }
}
#endif

State*
streetWalkGeneral(EdgePayload* superthis, State* state, WalkOptions* options, int forward) {
  Street* this = (Street*)superthis;
  State* ret = stateDup( state );
  
  float average_grade = 0;
  if (this->length > 0) {
    average_grade = (this->rise-this->fall)/this->length;
  }
  float average_speed = speed_from_grade(options, average_grade);
  
  long delta_t = this->length / average_speed;
  
  long delta_w = delta_t*options->walking_reluctance + this->rise*options->hill_reluctance;
  if( delta_w < 0 ) {
      delta_w = 0;
  }

  // max_walk overage considerations
  double end_dist = state->dist_walked + this->length;
  if(end_dist > options->max_walk)
    delta_w += (end_dist - options->max_walk)*options->walking_overage*delta_t;
  
  // turning considerations
  if( state->prev_edge &&
      state->prev_edge->type == PL_STREET &&
      ((Street*)state->prev_edge)->way != this->way ) {
    delta_w += options->turn_penalty;
  }

  if( forward ) {
    elapse_time_and_service_period_forward(ret, state, delta_t);
  } else {
    elapse_time_and_service_period_backward(ret, state, delta_t);
  }

  if (end_dist > ABSOLUTE_MAX_WALK) //TODO profile this to see if it's worth it
    ret->weight = MAX_LONG;
  else
    ret->weight       += this->slog*delta_w;
  ret->dist_walked    = end_dist;
  ret->prev_edge = superthis;

  return ret;
}

State*
streetWalk(EdgePayload* superthis, State* state, WalkOptions* options) {
    return streetWalkGeneral(superthis, state, options, TRUE);
}

State*
streetWalkBack(EdgePayload* superthis, State* state, WalkOptions* options) {
    return streetWalkGeneral(superthis, state, options, FALSE);
}
